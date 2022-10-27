function [data, nsym, errors, SNR] = processQAM(M, block_length, symbol_rate, fc, symbols_to_drop, rcf_rolloff, original_sample_frame, rate_samp, captured_samples, debug, diagnostics_on)
% processQAM decodes the QAM waveform contained in the structure waveform.
% waveform contains all previously-loaded data and settings.

%fprintf("\nDEBUG and DIAGNOSTICS are hard-coded on in processQAM.m!\n");
%diagnostics_on = 1;
%debug = 1;

%% EXTRACT SETTINGS FROM THE STRUCTURE
% Set these parameters correctly before running the script.
%% these can be loaded from the original .mat waveform struct.

% M is the number of QAM symbols; usually a power of 2.
%block_length = block_length; % number of symbols per marker frame.
% symbol rate is the number of symbols per second
signal = captured_samples(:);
% rate_samp is the oscilloscope sample rate.
% fc is the center frequency of the signal.
original_symbol_frame = qamdemod(original_sample_frame, M);

%% MIX WITH THE LOCAL OSCILLATOR
% Create the time vector
tmin = 0;
tmax = tmin + (1/rate_samp)*(length(signal)-1);
time_full = (tmin:(1/rate_samp):(tmax))';
% Mix the signal
signal = signal.*exp(1j*2*pi*fc*time_full);

%% FILTER OUT THE 2x FREQUENCY COMPONENT via RRCF
signal_I = real(signal);
signal_Q = imag(signal);

% Take the Fourier Transform (needed for cosine filtering)
%[f_S2, s_S2] = singfourSAFE(t_upsampled, S2_upsampled);
[f_spectrum, spectrum_I] = singfourSAFE(time_full, signal_I);
[~,    spectrum_Q] = singfourSAFE(time_full, signal_Q);

% Build the root-raised cosine filter
% center frequency, bandwidth, and rolloff are passed in as arguments.
s_rrcf = rrcf(f_spectrum, 0, symbol_rate, rcf_rolloff);

% Apply the RRCF
%s_S3 = s_S2.*(s_rrcf);
spectrum_I = spectrum_I.*(s_rrcf);
spectrum_Q = spectrum_Q.*(s_rrcf);

% IFFT back to time domain
%[~, S3_pulseshape] = invsingfourSAFE(f_S2, s_S3);
[~, signal_I] = invsingfourSAFE(f_spectrum, spectrum_I);
[~, signal_Q] = invsingfourSAFE(f_spectrum, spectrum_Q);

% Recombine I and Q channels
signal = signal_I + 1j*signal_Q;

if diagnostics_on
    figure(100); clf; hold on; axis equal;
    title("Mixed and filtered")
    plot(signal, '.', 'MarkerSize', 5);
    % plot(8*signal, '.', 'MarkerSize', 5);
end

%% EXTRACT, SCALE, AND INTERPOLATE THE WAVEFORM
% This occurs after mixing so we can sample the baseband waveform at a
% lower sampling rate.  Otherwise, the Nyquist constraint would force us to
% use a high resampling rate to avoid ailising the carrier, which consumes
% more memory and results in higher runtime.

% Calculate samples per symbol, and force it do be an integer.
% (An integer SPS is required by communication toolbox system objects)
% Different RCF rolloffs have varrying excess bandwidth.
safety = 1.1 + rcf_rolloff; 

% Use this sample rate if you have NOT mixed the signal down.
%rate_samp_min = ceil(2*(fc + (safety)*symbol_rate/2));

% Use this sample rate for a baseband signal.
rate_samp_min = (2*symbol_rate*safety);

% Observe the Nyquist limit.
sps_min = ceil(rate_samp_min/symbol_rate);
sps = 2*ceil(sps_min/2); % SPS should be even.

% NOTE: SPS should almost certianly be 4.


if debug
    fprintf("Original SPS is %.2f, new is %i.\n", rate_samp/symbol_rate, sps)
end
rate_samp = sps*symbol_rate;

% Create downsampled time (query) vector
time = (0:(1/rate_samp):tmax)';

% Downsample by interpolation
signal = interp1(time_full, signal, time, 'spline');

%{
% Make the time-domain waveform zero-mean
signal = signal - mean(signal);

% Apply a uniform gain so signal peak is unity
signal = signal/max(abs(signal));
%signal = signal/(sqrt(mean(abs(signal.^2))));

%% MIX WITH THE LOCAL OSCILLATOR
% Mix the signal
%signal = signal.*exp(1j*2*pi*fc*time);
%}

% Diagnostics
if diagnostics_on
    figure(100); clf; hold on; axis equal;
    title("Downsampled")
    plot(signal, '.', 'MarkerSize', 5);
    % plot(8*signal, '.', 'MarkerSize', 5);
end

%% AUTOMATIC GAIN CONTROL
% Attempts to smooth out fading and hold the signal power constant
automaticGainControl = comm.AGC;
    automaticGainControl.AdaptationStepSize = .002;
    automaticGainControl.DesiredOutputPower = .005; %W
    automaticGainControl.MaxPowerGain = 60; % dB

[signal, powerLevel] = automaticGainControl(signal);

% Diagnostics
if diagnostics_on
    %fprintf('AGC\n');
    
    % Main plot
    figure(100);
    title("AGC")
    plot(signal, '.', 'MarkerSize', 4);
    axis equal;
    
    % Power amplification level
    %{
    figure(101); clf;
    title("Power amplification level")
    plot(time, powerLevel);
    xlabel("Time (s)"); ylabel("Power (units?)");
    %}
end

%% RAISED COSINE FILTERING 
% Removes the 2x frequency component and performs pulse-shaping.
%{
rxfilter = comm.RaisedCosineReceiveFilter;
    rxfilter.Shape = 'Square root';
    rxfilter.RolloffFactor = rcf_rolloff;
    rxfilter.FilterSpanInSymbols = 6;
    rxfilter.InputSamplesPerSymbol = sps;
    rxfilter.DecimationFactor = 1;
    rxfilter.DecimationOffset = 0;
    rxfilter.Gain = 1;
    
signal = rxfilter(signal);

if diagnostics_on
    %fprintf('RCF\n');
    
    % Main plot
    figure(100);
    title("Filtering")
    plot(signal, '.', 'MarkerSize', 3);
    axis equal;
end
%}


warning('off','comm:CoarseFrequencyCompensator:NeedTooMuchMemory');
%% COARSE FREQUENCY COMPENSATION
% Corrects Clock Skew
modtype = "QAM";
if M == 2
    modtype = "BPSK";
elseif M == 4
    modtype = "QPSK";
end
coarseFrequencyComp = comm.CoarseFrequencyCompensator;
    coarseFrequencyComp.Modulation = modtype;
    % coarseFrequencyComp.Algorithm = 'FFT-based';
    % Use Correlation-based for HDL implementation, but see documentation
    % first.
    coarseFrequencyComp.FrequencyResolution = 10e4; % Hz
    %coarseFrequencyComp.MaximumFrequencyOffset = 10e3; % Hz
    coarseFrequencyComp.SampleRate = rate_samp; % Hz
    %coarseFrequencyComp.SamplesPerSymbol = sps; % Hz, for OQPSK only

[signal, ~] = coarseFrequencyComp(signal);
upsampled = signal;


if diagnostics_on
    %fprintf('Freq. Comp.\n');
    
    % Main plot
    figure(100);
    title("Coarse freq comp")
    plot(signal, '.', 'MarkerSize', 2);
    axis equal;
end


%% TIMING RECOVERY
% (Symbol Synchronization)
symbolSync = comm.SymbolSynchronizer;
    symbolSync.Modulation = 'PAM/PSK/QAM';
    symbolSync.TimingErrorDetector = 'Zero-Crossing (decision-directed)';
    symbolSync.SamplesPerSymbol = sps;
    symbolSync.DampingFactor = 5;
    symbolSync.NormalizedLoopBandwidth = 0.02;
    symbolSync.DetectorGain = 1;

%signal(isnan(signal)) = 0;
[signal, timing_error] = symbolSync(signal);

% From here on, we're working with samples of the waveform.
% Create a timing vector for symbol time.
time_samples_full = 0:(1/symbol_rate):((length(signal)-1)*(1/symbol_rate));
%time_samples_full_2 = [time(1:8:end)]; % Needs an extra sample at the end.


%len_after = length(signal)
%len_before - len_after
%len_before / len_after

if diagnostics_on
    %fprintf('Symbol Sync (timing recovery)\n');
    
    % Main plot
    figure(100);
    title("Symbol Sync")
    plot(signal, '.', 'MarkerSize', 1);
    axis equal;
    
    % Timing error
    
    figure(102); clf; hold on;
        timing_unwrapped = unwrap(timing_error*2*pi)/(2*pi);
        timing_unwrapped = timing_unwrapped - timing_unwrapped(end);
        plot(time,timing_unwrapped, '.');
        title('Symbol Timing Error (timing recovery)');
        xlabel('Time (s)');
        ylabel('Timing Error (samples)');
    %}
end

%% FINE FREQUENCY COMPENSATOR
% (Performs Carrier Synchronization)
modtype = "QAM";
if M == 2
    modtype = "BPSK";
elseif M == 4
    modtype = "QPSK";
end

carrSync = comm.CarrierSynchronizer;
    carrSync.Modulation = modtype;
    carrSync.ModulationPhaseOffset = 'Auto';
    %carrSync.CustomPhaseOffset = 0;
    carrSync.SamplesPerSymbol = 1;
    carrSync.DampingFactor = 10;
    carrSync.NormalizedLoopBandwidth = 0.05; % 0.01


carrSync_eye = comm.CarrierSynchronizer;
    carrSync_eye.Modulation = carrSync.Modulation;
    carrSync_eye.ModulationPhaseOffset = carrSync.ModulationPhaseOffset;
    %carrSync_eye.CustomPhaseOffset = carrSync.CustomPhaseOffset;
    carrSync_eye.SamplesPerSymbol = sps; %fs/(baud)
    carrSync_eye.DampingFactor = carrSync.DampingFactor;
    carrSync_eye.NormalizedLoopBandwidth = carrSync.NormalizedLoopBandwidth; % 0.01

    
[signal, error_phase] = carrSync(signal);
[full_signal_ffc, ~] = carrSync_eye(upsampled);

full_signal_ffc = circshift(full_signal_ffc, 0);


if diagnostics_on

    if M == 2 || M == 4
        label = modtype;
    else
        label = sprintf("%i-QAM", M);
    end

    % Eye diagram
    % eye_traces will be a pxq array, where p is the number of samples to 
    % show on the eye diagram (samples per symbol times number of symbols 
    % to display), and q is the number of traces we want to show.
    n_traces = 600;
    k = 4; %4*block_length;
    % Knock off bad samples
    signal_eye = full_signal_ffc((1+symbols_to_drop*sps):end);
    % reshape the array to the pxq dimensions described above.
    eye_traces = reshape(signal_eye(1:(end-mod(length(signal_eye), k*sps))), k*sps, []);
    % Show the real axis, and take traces from the end of the data in case
    % symbols_to_drop isn't large enough.
    eye_traces = real(eye_traces(:, ((end-n_traces):1:(end-1))));
    figure(103);
        plot(time(1:(k*sps))*1e9, real(eye_traces), '-', 'Color', [1, 1, 1, 0.1]);
        title(sprintf("%.1f Gbd %s Eye Diagram", symbol_rate/1e9, label));
        xlabel("Time (ns)");
        ylabel("Arbitrary Units");
        
    % Main plot
    figure(100);
        %plot(signal_eye, '.', 'MarkerSize', 1);
        plot(signal, '.', 'MarkerSize', 1);
        axis equal;
    
    % Phase error
    figure(104); clf;
        plot(error_phase);
        title('Phase Error (fine frequency compensator)');
        xlabel('symbol number');
        ylabel('radians');

    % Time-domain trace with sample times marked
    figure(108); clf; hold on;
        plot(time, real(full_signal_ffc), '-');
        plot(time, imag(full_signal_ffc), '-');

        plot(time_samples_full - 4/rate_samp, real(signal), 'x', 'MarkerSize', 5);
        plot(time_samples_full - 4/rate_samp, imag(signal), 'x', 'MarkerSize', 5);
end


%% SCALE AND TRUNCATE THE PROCESSED WAVEFORM

% Scaling
samples_full = signal/mean(abs(signal));

% Truncate the waveform to remove settling time
start = symbols_to_drop;
stop = length(samples_full);
samples_full = samples_full(start:stop);
time_samples_full = time_samples_full(start:stop);

% Calculate the number of frames we should expect.
t_frame = block_length/symbol_rate; % The time spanned by a single frame.
n_frames = floor((time_samples_full(end)-time_samples_full(1))/t_frame);

% Duplicate the original symbol vector to match measured sample dimensions.
original_symbols = repmat(original_symbol_frame, n_frames, 1);
original_sample_frame = repmat(original_sample_frame, n_frames, 1);

% Create symbol time vector (subset of the full-length symbol-time vector)
time_samples = time_samples_full(1:(block_length*n_frames));

% Now, trim the sample vector to be exactly an integer multiple of the 
% number of symbols per frame.
% It is better to take frames from the end and discard extra samples at
% the beginning, since these are more likely to be contaminated by
% "spin-up time" for the filters and phase-lock loops.
samples = samples_full((end-block_length*n_frames+1):end);



%% Preamble Detection

%% Frame Synchronization

%% Data Demodulation


%% Get the SER

% The first thing to do is to align the measured and original symbols

% Set up for the shift-determination loop
header = original_symbols(1:32); % Look for this pattern in the RX data.
shifts = 1:(length(original_symbols)-length(header));
n_errors_min = numel(samples);
phi_0_ideal = 0;
shift_ideal = 0;

%fprintf("%i, %i, %i\n", length(original_symbols), length(shifts), length(samples));
% 349280, 349264, 349280

% Now, try to determine the shift between the original and measured data.
% We will do this four times (one for each of the four N*pi/2 radian
% rotations of the constallation diagram), and select the shift and
% rotation combination that yields the minimum number of errors.
for n = 0:3
    % Set phase offset (rotation) angle
    phi_0 = n*pi/2;
    
    % Demodulate the sampled symbols.
    symbols = qamdemod(exp(1j*phi_0)*samples, M);

    result = zeros(length(shifts), 1);
    for s = shifts
        result(s) = sum(header == symbols(s:(s+length(header)-1)));
    end
    
    % Shift the measured data to align.
    [~,idx] = max(result);
    symbols = circshift(symbols, -idx+1);

    % Diagnostic: see how the symbols compare. Helps debug rotation and
    % decoding problems.
    
    %{
    check = 1:31;
    fprintf("\n Decoded: ");
    fprintf("%i, ", symbols(check));
    fprintf("\n Original: ");
    fprintf("%i, ", original_symbols(check));
    fprintf("\n");
    %}

    % Now get the SER.
    %symbols = reshape(symbols, block_length, n_frames);
    n_errors = sum(original_symbols ~= symbols);
    
    if n_errors < n_errors_min
        n_errors_min = n_errors;
        phi_0_ideal = phi_0;
        shift_ideal = -idx+1;
        n_errors_ideal = n_errors;
    end
end

% Do it all again one last time now that we know the best shift and phase.
%samples_full = exp(1j*phi_0_ideal)*samples_full;
samples = exp(1j*phi_0_ideal)*samples;
symbols = qamdemod(samples, M);

%samples_full = circshift(samples_full, shift_ideal);
samples = circshift(samples, shift_ideal);
symbols = circshift(symbols, shift_ideal);


%% Get the SNR of the signal
% Method: subtract the original sample values from the measured ones.
% The difference between the two is noise (assuming correct scaling).

samp_meas = samples/mean(abs(samples));
samp_orig = original_sample_frame/mean(abs(original_sample_frame));

% Contains both noise and ISI
% Get the VOLTAGE SIGNAL noise (not power).
noise_voltage = (samp_meas - samp_orig);

% Get the SNR, in dB.  Takes voltages as inputs, not powers.
SNR = snr(samp_orig, noise_voltage);

if diagnostics_on
    % Show noise on a constellation diagram
    figure(105); clf; hold on;
    plot(awgn(samp_orig + j*eps, SNR), '.');
    plot(samp_meas + j*eps, '.');
    plot(samp_orig + j*eps, '+');
    title("Noise Comparison Constellation");
    legend("AWGN at SNR", "Measured", "Ideal");
    axis equal;

    % Show noise spectrum
    figure(106); clf; hold on;
    [f, s_n_meas] = singfourSAFE(time_samples, noise_voltage.^2);
    [~, s_n_awgn] = singfourSAFE(time_samples, (awgn(samp_orig, SNR) - samp_orig).^2);
    plot(f, abs(s_n_meas), f, abs(s_n_awgn));
    title("Noise Power Spectrum");
    xlabel("Frequency (Hz)");
    
    % Mark sample times on time-domain waveform
    figure(107); clf; hold on;
    plot(time_samples, imag(samples), 'x');
    plot(time_samples, real(samples), 'x');
    title("Samples in Time Domain");
    legend("Q channel", "I channel");
end


% Calculate the bit errors.
biterrors = 0;
bitdiff = bitxor(symbols,original_symbols);
for idx_sym = 1:length(bitdiff)
    biterrors = biterrors + sum(bitget(bitdiff(idx_sym), log2(M):-1:1));
end

% Collect and hand back all the important information
nsym = numel(symbols);

errors = struct;
errors.bit = biterrors;
errors.sym = n_errors_ideal;

data = struct;
data.symbols = symbols;
data.samples = samples;


end
