function [data, nsym, errors, SNR] = processQAM(mod_order, block_length, sym_rate, IF_estimate, symbols_to_drop, rcf_rolloff, original_samples, samp_rate, captured_samples, debug, diagnostics_on)
% processQAM decodes the QAM waveform contained in the structure waveform.
% waveform contains all previously-loaded data and settings.

%diagnostics_on = 1;
%debug = 1;

%% EXTRACT SETTINGS FROM THE STRUCTURE
% Set these parameters correctly before running the script.
%% these can be loaded from the original .mat waveform struct
M = mod_order; % Equal to the number of QAM symbols.
%block_length = block_length; % number of symbols per marker frame.
symbol_rate = sym_rate; % symbol rate
%symbol_rate = sym_rate*(63.90039/64);

signal = captured_samples;
sample_rate = samp_rate; % Oscilloscope sample rate.
f_LO = IF_estimate;

original_sample_frame = original_samples;
original_symbol_frame = qamdemod(original_sample_frame, M);

modtype = sprintf("%i-QAM", M);
if M == 2
    modtype = "BPSK";
elseif M == 4
    modtype = "QPSK";
end

%% EXTRACT, SCALE, AND INTERPOLATE THE WAVEFORM
% Create the time vector
tmin = 0;
tmax = tmin + (1/sample_rate)*(length(signal)-1);
time_full = (tmin:(1/sample_rate):(tmax))';

% Calculate samples per symbol, and force it do be an integer.
% (An integer SPS is required by communication toolbox system objects)
sps = 8; %2*floor(sample_rate/(2*symbol_rate)); % sps should be even.  I don't know why.
if debug
    fprintf("Original SPS is %.2f, New is %i.\n", sample_rate/symbol_rate, sps)
end
sample_rate = sps*symbol_rate;

% Create downsampled time (query) vector
time = (0:(1/sample_rate):tmax)';

% Downsample by interpolation
signal = interp1(time_full, signal, time, 'makima');

% Make the time-domain waveform zero-mean
signal = signal - mean(signal);

% Apply a uniform gain so signal peak is unity
signal = signal/max(abs(signal));


%% MIX WITH THE LOCAL OSCILLATOR
% Mix the signal
signal = signal.*exp(1j*2*pi*f_LO*time);

% Diagnostics
if diagnostics_on
    figure(100); clf; hold on;
    title("Mixed signal")
    plot(signal, '.', 'MarkerSize', 5);
    % plot(8*signal, '.', 'MarkerSize', 5);
end

%% AUTOMATIC GAIN CONTROL
% Attempts to smooth out fading and hold the signal power constant
automaticGainControl = comm.AGC;
    automaticGainControl.AdaptationStepSize = .0001;
    automaticGainControl.DesiredOutputPower = 1; %W
    automaticGainControl.MaxPowerGain = 60; % dB

[signal, powerLevel] = automaticGainControl(signal);

% Diagnostics
if diagnostics_on
    %fprintf('AGC\n');
    
    % Main plot
    figure(100);
    title("AGC")
    plot(signal, '.', 'MarkerSize', 4);
    
    % Power amplification level
    %{
    figure(1); clf;
    title("Power amplification level")
    plot(time, powerLevel);
    xlabel("Time (s)"); ylabel("Power (units?)");
    %}
end

%% RAISED COSINE FILTERING 
% Removes the 2x frequency component and performs pulse-shaping.
rxfilter = comm.RaisedCosineReceiveFilter;
    rxfilter.Shape = 'Square root';
    rxfilter.RolloffFactor = rcf_rolloff;
    rxfilter.FilterSpanInSymbols = 12;
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
end


warning('off','comm:CoarseFrequencyCompensator:NeedTooMuchMemory');
%% COARSE FREQUENCY COMPENSATION
% Corrects Clock Skew
coarseFrequencyComp = comm.CoarseFrequencyCompensator;
    coarseFrequencyComp.Modulation = 'QAM';
    % coarseFrequencyComp.Algorithm = 'FFT-based';
    % Use Correlation-based for HDL implementation, but see documentation
    % first.
    coarseFrequencyComp.FrequencyResolution = 1e3; % Hz
    %coarseFrequencyComp.MaximumFrequencyOffset = 10e3; % Hz
    coarseFrequencyComp.SampleRate = sample_rate; % Hz
    %coarseFrequencyComp.SamplesPerSymbol = sps; % Hz, for OQPSK only

[signal, errorFreqOffset] = coarseFrequencyComp(signal);
upsampled = signal;


% From here on, we're working with a samples of the waveform.
% Create a timing vector for symbol time.
time_samples_full = 0:(1/symbol_rate):((length(signal)-1)*(1/symbol_rate));

if diagnostics_on
    %fprintf('Freq. Comp.\n');
    
    % Main plot
    figure(100);
    title("Coarse freq comp")
    plot(signal, '.', 'MarkerSize', 2);
end

%% TIMING RECOVERY
% (Symbol Synchronization)
symbolSync = comm.SymbolSynchronizer;
    symbolSync.Modulation = 'PAM/PSK/QAM';
    symbolSync.TimingErrorDetector = 'Zero-Crossing (decision-directed)';
    symbolSync.SamplesPerSymbol = sps;
    symbolSync.DampingFactor = 10;
    symbolSync.NormalizedLoopBandwidth = 0.001;
    symbolSync.DetectorGain = 1;

    
%signal(isnan(signal)) = 0;
[signal, timing_error] = symbolSync(signal);

if diagnostics_on
    %fprintf('Symbol Sync (timing recovery)\n');
    
    % Main plot
    figure(100);
    title("Symbol Sync")
    plot(signal, '.', 'MarkerSize', 1);
    
    % Timing error
    
    figure(2); clf; hold on;
        timing_unwrapped = unwrap(timing_error*2*pi)/(2*pi);
        timing_unwrapped = timing_unwrapped - timing_unwrapped(end);
        plot(time_samples_full,timing_unwrapped, '.');
        title('Symbol Timing Error (timing recovery)');
        xlabel('Time (s)');
        ylabel('Timing Error (samples)');
    %}
end

%% FINE FREQUENCY COMPENSATOR
% (Performs Carrier Synchronization)
carrSync = comm.CarrierSynchronizer;
    carrSync.Modulation = 'QAM';
    carrSync.ModulationPhaseOffset = 'Auto';
    %carrSync.CustomPhaseOffset = 0;
    carrSync.SamplesPerSymbol = 1;
    carrSync.DampingFactor = 1;
    carrSync.NormalizedLoopBandwidth = 0.001; % 0.01


carrSync_eye = comm.CarrierSynchronizer;
    carrSync_eye.Modulation = carrSync.Modulation;
    carrSync_eye.ModulationPhaseOffset = 'Auto';
    %carrSync_eye.CustomPhaseOffset = 0;
    carrSync_eye.SamplesPerSymbol = sps; %fs/(baud)
    carrSync_eye.DampingFactor = 1;
    carrSync_eye.NormalizedLoopBandwidth = 0.01; % 0.01

    
[signal, error_phase] = carrSync(signal);
[signal_eye, ~] = carrSync_eye(upsampled);

signal_eye = circshift(signal_eye, 0);

%fprintf("%i\n", round(timing_error(1)*sample_rate))

%{
nsym = 1;
SNR = 10;

errors = struct;
errors.bit = 10;
errors.sym = 10;

data = struct;
data.symbols = 100;
data.samples = 100;
return
%}

k = 4; %4*block_length;
signal_eye = signal_eye((1+symbols_to_drop*sps):end);
eye_traces = reshape(signal_eye(1:(end-mod(length(signal_eye), k*sps))), k*sps, []);
eye_traces = eye_traces(:, (1:1:600))./sqrt(2);

if diagnostics_on
    %fprintf('Carrier Sync.\n');
    
    % Main plot
    
    figure(100);
        plot(signal_eye, '.', 'MarkerSize', 1);
        
    figure(100);
        title("Carrier Sync")
        plot(signal, '.', 'MarkerSize', 1);
        
    figure(101);
        plot(time(1:(k*sps))*1e9, real(eye_traces*exp(1j*pi/4)), '-', 'Color', [1, 1, 1, 0.1]);
        title(sprintf("%.1f Gbd %s Eye Diagram", symbol_rate/1e9, modtype));
        xlabel("Time (ns)");
        ylabel("Arbitrary Units");
        
    % Phase error
    figure(3); clf;
        plot(error_phase);
        title('Phase Error (fine frequency compensator)');
        xlabel('symbol number');
        ylabel('radians');

end


%% SCALE AND TRUNCATE THE PROCESSED WAVEFORM

% Scaling
samples_full = signal/max(abs(signal));

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
original_samples = repmat(original_sample_frame, n_frames, 1);

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
    phi_0 = n*pi/2 + pi/4;
    
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
    check = 300:330;
    fprintf("\n Decoded: ");
    fprintf("%.0f, ", symbols(check));
    fprintf("\n Original: ");
    fprintf("%.0f, ", original_symbols(check));
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
samp_orig = original_samples/mean(abs(original_samples));

% Contains both noise and ISI
% Get the VOLTAGE SIGNAL noise (not power).
noise_v = (samp_meas - samp_orig);

% Get the SNR, in dB.  Takes voltages as inputs, not powers.
SNR = snr(samp_orig, noise_v);

if diagnostics_on
    % Show noise on a constellation diagram
    figure(4); clf; hold on;
    plot(awgn(samp_orig, SNR), '.');
    plot(samp_meas, '.');
    plot(samp_orig, '+');
    title("Noise Comparison Constellation");
    legend("AWGN at SNR", "Measured", "Ideal");

    % Show noise spectrum
    %figure(5); clf; hold on;
    %[f, s_n_meas] = singfourSAFE(time_samples, noise_v.^2);
    %[~, s_n_awgn] = singfourSAFE(time_samples, (awgn(samp_orig, SNR) - samp_orig).^2);
    %plot(f, abs(s_n_meas), f, abs(s_n_awgn));
    %title("Noise Power Spectrum");
    %xlabel("Frequency (Hz)");
    
    % Mark sample times on time-domain waveform
    figure(6); clf; hold on;
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
