function [data, nsym, errors, SNR_est, SNR_raw, weights] = processQAM(M, block_length, symbol_rate, fc, rcf_rolloff, original_sample_frame, rate_samp, captured_samples, diagnostics_on, eq_on)
% Updated to use verified fourier transforms

weights = 1;  % If the EQ is used, it will populate this placeholder.
% processQAM decodes the QAM waveform contained in the structure waveform.
% waveform contains all previously-loaded data and settings.

%fprintf("DEBUG and DIAGNOSTICS are hard-coded OFF in processQAM.m!\n");
%diagnostics_on = 1;

%% EXTRACT SETTINGS FROM THE STRUCTURE
% Set these parameters correctly before running the script.
% These can be loaded from the original .mat waveform struct.
% M is the number of QAM symbols; usually a power of 2.
% block_length is the number of symbols per marker frame.
% symbol rate is the number of symbols per second
% rate_samp is the oscilloscope sample rate.
% fc is the center frequency of the signal.

% Convert the original samples into demodulated symbols
original_symbol_frame = qamdemod(original_sample_frame, M);
sample_period = 1/rate_samp;

% Set up the signal and time vectors.
signal = captured_samples(:);
duration = (numel(signal))*sample_period;
time_in = 0:sample_period:(duration-sample_period);
time_in = time_in(:);

% Make the time-domain waveform zero-mean
signal = signal - mean(signal);

% Apply a uniform gain so signal peak is unity
signal = signal/(sqrt(mean(abs(signal.^2))));


%% DIRECTLY CALCULATE SNR
% This calculates the SNR of the signal after RRCF filtering.  If
% you make a signal, add noise using awgn(), then feed it into this
% program, the calculated SNR will be greater than expected due to the
% matched filter.

scale = 1/numel(signal);
s = scale*fftshift(fft(signal));
f = (-numel(s)/2:numel(s)/2-1)/numel(s)*rate_samp; f = f(:);
%f = f + fc;

% Build the root-raised cosine filter
filt = rrcf(f, fc, symbol_rate, rcf_rolloff);

% Representative noise should be outside the filter bandwidth, away from DC
% to avoid 1/f components, and below fc to avoid grabbing anything beyond
% the scope's front-end amplifier cutoff.
occupied_bw = symbol_rate*(1 + rcf_rolloff);
finv = (filt <= 1e-5) & (abs(f) > 1e3) & (abs(f - occupied_bw) < fc); 

s_sig_filt = s.*filt;  % Filtered signal.
s_noise = repmat(s(finv), [ceil(numel(s)/sum(finv)), 1]);
s_noise = s_noise(1:numel(s)); % Representative noise vector.
s_noise_filt = s_noise.*filt; % Filtered noise

%{
figure(217); clf; hold on;
plot(f, 20*log10(abs(s)));
plot(f, 20*log10(abs(s_noise)));
plot(f, 20*log10(abs(s_noise_filt)));
plot(f, 20*log10(abs(s_sig_filt)));
%}

% IFFT back to time domain
tdsigfilt = ifft(fftshift(s_sig_filt)/scale);
tdnoisefilt = ifft(fftshift(s_noise_filt)/scale);

tdsigfiltpow = sum(abs(tdsigfilt(:)).^2)/numel(tdsigfilt);
tdnoisefiltpow = sum(abs(tdnoisefilt(:)).^2)/numel(tdnoisefilt);

% This is the SNR of the signal after filtering.
SNR_raw = 10*log10(abs(tdsigfiltpow/tdnoisefiltpow));


%% MIX THE SIGNAL WITH A LOCAL OSCILLATOR
carrier_cycles = (duration)*fc;
extra_cycles = mod(carrier_cycles, 1);
%
if extra_cycles < 0.5
    % Decrease fc
    fc = fc*(1 - (extra_cycles/carrier_cycles));
else
    % Increase fc
    fc = fc*(1 + ((1-extra_cycles)/carrier_cycles));
end
%}
signal = signal.*exp(1j*2*pi*fc*time_in);

%% FILTER OUT THE 2x FREQUENCY COMPONENT via RRCF
scale = 1/numel(signal);
s = scale*fftshift(fft(signal));
f = (-numel(s)/2:numel(s)/2-1)/numel(s)*rate_samp;
%f = f + fc;

% Build the root-raised cosine filter
filt = rrcf(f, 0, symbol_rate, rcf_rolloff);

% Apply the RRCF
s = s.*filt;

% IFFT back to time domain
signal = ifft(fftshift(s)/scale);

if diagnostics_on
    figure(100); clf; hold on; axis equal;
    title("Mixed and filtered")
    plot(signal, '.', 'MarkerSize', 5);
end

%% EXTRACT, SCALE, AND INTERPOLATE THE WAVEFORM
% This occurs after mixing so we can sample the baseband waveform at a
% lower sampling rate.  Otherwise, the Nyquist constraint would force us to
% use a high resampling rate to avoid ailising the carrier, which consumes
% more memory and results in higher runtime.

% Calculate samples per symbol, and force it do be an integer.
% (An integer SPS is required by communication toolbox system objects)
% Different RCF rolloffs have varrying excess bandwidth.
excess_bw = 1.1 + rcf_rolloff; % Excess bandwidth is 1+beta, but use 1.1 for safety.
rate_samp_min = (2*symbol_rate*excess_bw);

% Observe the Nyquist limit.
sps_min = rate_samp_min/symbol_rate;
sps = 2*ceil(sps_min/2); % SPS should be even, and almost certianly 4.
rate_samp = sps*symbol_rate;

% Create downsampled time (query) vector.
% From here until sampling, time corresponds to signal.
time = 0:(1/rate_samp):(duration - 1/rate_samp);
time = time(:);

% Downsample by interpolation
signal = interp1(time_in, signal, time, 'spline');

% Diagnostics
if diagnostics_on
    figure(100);
    title("Downsampled")
    plot(signal, '.', 'MarkerSize', 5);
end

%% AUTOMATIC GAIN CONTROL
%{
% Attempts to smooth out fading and hold the signal power constant
automaticGainControl = comm.AGC;
    automaticGainControl.AdaptationStepSize = .002;
    automaticGainControl.DesiredOutputPower = 1; %W
    automaticGainControl.MaxPowerGain = 60; % dB

[signal, powerLevel] = automaticGainControl(signal);

% Diagnostics
if diagnostics_on
    figure(100);
    title("AGC")
    plot(signal, '.', 'MarkerSize', 4);
    axis equal;
end
%}

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
    coarseFrequencyComp.Algorithm = 'FFT-based';
    coarseFrequencyComp.FrequencyResolution = 10e3; % Hz
    coarseFrequencyComp.SampleRate = rate_samp; % Hz
[signal, ~] = coarseFrequencyComp(signal);

if diagnostics_on
    figure(100);
    title("Coarse freq comp")
    plot(signal, '.', 'MarkerSize', 2);
    axis equal;
end

%% FINE FREQUENCY COMPENSATOR
% (Performs Carrier Synchronization and removes phase offset)
% We do this before the symbol decision timing recovery because it will
% fail if the symbols are clustered on a decision boundary, and FFC ensures
% that this will not be the case.

% Use my own function to do this.  Not practical for real-time or
% low-latency systems, but has less noise than the comm system object.
order = 1; % Linear fit to frequency drift.
topn = 50; % Use the topn most powerful symbols for the offset estimation.
chunk = 1000; % Consider <chunk> symbols at a time.
signal = manual_ffc(signal, order, topn, M, chunk);

if diagnostics_on
    figure(100);
    title("First Phase Offset Removal");
    plot(signal, '.', 'MarkerSize', 2);
    axis equal;
end

%{
carrSync = comm.CarrierSynchronizer;
    carrSync.Modulation = modtype;
    carrSync.ModulationPhaseOffset = 'Auto';
    %carrSync.CustomPhaseOffset = 0;
    carrSync.SamplesPerSymbol = sps;
    carrSync.DampingFactor = 10;
    carrSync.NormalizedLoopBandwidth = 0.05; % 0.01
[signal, error_phase] = carrSync(signal);

if diagnostics_on
    figure(100);
    title("Fine freq comp");
    plot(signal, '.', 'MarkerSize', 2);
    axis equal;
end
%}

%% TIMING RECOVERY
% (Symbol Synchronization)
% Zero-crossing method — The zero-crossing method is a decision-directed 
% technique that requires 2 samples per symbol at the input to the 
% synchronizer. It is used in low-SNR conditions for all values of excess 
% bandwidth and in moderate-SNR conditions for moderate excess bandwidth 
% factors in the approximate range [0.4, 0.6].

% Mueller-Muller method — The Mueller-Muller method is a decision-directed 
% feedback method that requires prior recovery of the carrier phase. When 
% the input signal has Nyquist pulses (for example, when using a raised 
% cosine filter), the Mueller-Muller method has no self noise. For 
% narrowband signaling in the presence of noise, the performance of the 
% Mueller-Muller method improves as the excess bandwidth factor of the 
% pulse decreases.

% Because the decision-directed methods (zero-crossing and Mueller-Muller) 
% estimate timing error based on the sign of the in-phase and quadrature 
% components of signals passed to the synchronizer, they are not 
% recommended for constellations that have points with either a zero 
% in-phase or a quadrature component.

symbolSync = comm.SymbolSynchronizer;
    symbolSync.Modulation = 'PAM/PSK/QAM';
    symbolSync.TimingErrorDetector = 'Zero-Crossing (decision-directed)';
    symbolSync.SamplesPerSymbol = sps;
    symbolSync.DampingFactor = .707;
    symbolSync.NormalizedLoopBandwidth = 0.03;
    symbolSync.DetectorGain = 1;
[samples, timing_error] = symbolSync(signal);
%samples = samples / mean(abs(samples));

% From here on, we're working with samples of the waveform.
% Create a timing vector for symbol time.
time_samples = 0:(1/symbol_rate):((length(samples)-1)*(1/symbol_rate));
time_samples = time_samples(:);

if diagnostics_on
    % Main plot
    figure(100);
    title("Symbol Sync")
    plot(samples, '.', 'MarkerSize', 1);
    axis equal;
    
    % Timing error
    figure(102); clf; hold on;
    timing_unwrapped = unwrap(timing_error*2*pi)/(2*pi);
    timing_unwrapped = timing_unwrapped - timing_unwrapped(end);
    plot(time,timing_unwrapped, '.');
    title('Symbol Timing Error (timing recovery)');
    xlabel('Time (s)');
    ylabel('Timing Error (samples)');
end

%%  HACKY PHASE OFFSET REMOVAL - AGAIN!
% Do it again because we're probably not perfectly aligned to the ideal
% constellation.  Now that the symbol decision timing is corrected, we'll
% be able to get a better alignment.
% This would also be performed by the equalizer, but we handle it here
% since the EQ may not be used.
order = 1; % Linear fit to frequency drift.
topn = 1000;
samples = manual_ffc(samples, order, topn, M, chunk);

if diagnostics_on
    figure(100);
    title("Second Phase Offset Removal");
    plot(samples, '.', 'MarkerSize', 2);
    axis equal;
end


%% Preamble Detection and Frame Synchronization
% Sync the received data to the original data.  Do this before equalization
% so that the equalizer training sequence is in sync with the received
% data.  The EQ will fail if this is not the case.

% Set up for the shift-determination loop
header_sym = original_symbol_frame(1:(256)); % Look for this pattern in the RX data.
header_samp = repmat(original_sample_frame(1:256) + 1j*eps, [1,1]);

shifts = 1:(2*length(original_symbol_frame)-length(header_sym));
bestsofar = 0;
testsamples = repmat(samples(1:(numel(original_sample_frame))), [2,1]);
phi_0_ideal = 0;
idx_start = 0;

% Now, try to determine the shift between the original and measured data.
% We will do this four times (one for each of the four N*pi/2 radian
% rotations of the constallation diagram), and select the shift and
% rotation combination that yields the minimum number of errors.
nmax = 3;
theta = pi/2;
if M == 2
    nmax = 1;
    theta = pi;
end
for n = 0:nmax
    % Set phase offset (rotation) angle
    phi_0 = n*theta;
    
    % Demodulate the sampled symbols.
    testsymbols = qamdemod(exp(1j*phi_0)*testsamples, M);

    result = zeros(length(shifts), 1);
    for s = shifts
        result(s) = sum(header_sym == testsymbols(s:(s+length(header_sym)-1)));
    end
    [maxval,idx] = max(result);
    
    if maxval > bestsofar
        bestsofar = maxval;
        phi_0_ideal = phi_0;
        idx_start = idx;
    end
end
% Finally, rotate the measured data to align with the original...
samples = exp(1j*phi_0_ideal)*samples;

% .... and discard everything up until the beginning of a complete frame.
% We don't want to circshift the samples because this produces a time
% discontinuity where the end of the capture suddenly jumps to the
% beginning.
samples = samples(idx_start:end);


%% Equilization
% TO DO:  Set this up so I can pass in a set of static equalizer
% coefficients, and have the equalizer use those instead of training.  The
% purpose of this is to be able to de-embed effects of cables, etc, and
% observe only the effects of dispersion.

if eq_on
    samples = samples/mean(abs(samples));
    dfe = comm.DecisionFeedbackEqualizer('Algorithm','LMS', ...
    'NumForwardTaps',30,'NumFeedbackTaps',5,'StepSize',0.03);
    dfe.ReferenceTap = 3;
    dfe.Constellation = qammod((1:M)-1, M) + 1j*eps;

    [samples, err, weights] = dfe(samples(:), header_samp);

    % Remove equalizer start-up stuff
    %drop = 3*(dfe.NumForwardTaps + dfe.NumFeedbackTaps);
    drop = 300;
    samples = samples(drop:end);
    %samples = circshift(samples, -(dfe.ReferenceTap-1));

end
samples = samples / mean(abs(samples));


%% Scale and truncate the samples

% Take an integer number of frames from the front of the signal.
t_frame = block_length/symbol_rate; % The time spanned by a single frame.
n_frames = floor((numel(samples)/symbol_rate)/t_frame);
samples = samples(1:(block_length*n_frames));

% Sync the signal with the original data once again.  We need to do this
% because we've dropped the symbols affected by equalizer settling time,
% and now we can use circshift because the signal is an integer number of
% data frames in length.
[~, ~, D] = alignsignals(header_samp, samples);
D = D - block_length*abs(fix(D/block_length));
samples = circshift(samples, -D);

% Duplicate the original symbol vector to match measured sample dimensions.
original_symbols = repmat(original_symbol_frame, n_frames, 1);
original_samples = repmat(original_sample_frame, n_frames, 1);

% Finally, trim up the time vector
time_samples = time_samples(1:numel(samples));

if diagnostics_on
    % Main plot
    figure(100);
    title("Equalized and Truncated")
    plot(samples, '.', 'MarkerSize', 1);
    axis equal;
end

%% Data Demodulation
symbols = qamdemod(samples, M);


%% Get the SNR of the signal
% Method: subtract the original sample values from the measured ones.
% The difference between the two is noise (assuming correct scaling).

samples = samples/mean(abs(samples));
samp_orig = original_samples/mean(abs(original_samples));

% Contains both noise and ISI
% Get the VOLTAGE SIGNAL noise (not power).
noise_voltage = (samples - samp_orig);

% Get the SNR, in dB.  Takes voltages as inputs, not powers.
SNR_est = snr(samp_orig, noise_voltage);


%% Get the SER and BER
% Note: we don't calculate the BER/SNR directly, but instead hand back the
% number of bit errors and symbol errors, as well as the number of symbols
% sent.  This lets the user perform the calculation, and provides more
% useful information.

% Calculates the BER
biterrors = 0;
bitdiff = bitxor(symbols,original_symbols);
for idx_sym = 1:length(bitdiff)
    biterrors = biterrors + sum(bitget(bitdiff(idx_sym), log2(M):-1:1));
end

% Calculate the SER
symerrors = sum(symbols ~= original_symbols);

% Collect and hand back all the important information
nsym = numel(symbols);

errors = struct;
errors.bit = biterrors;
errors.sym = symerrors;

data = struct;
data.symbols = symbols;
data.samples = samples;

% Diagnostic: Show errors on a constellation diagram
if diagnostics_on
    idx_err = (symbols ~= original_symbols);

    % Show noise on a constellation diagram
    figure(105); clf; hold on;
    plot(awgn(samp_orig + 1j*eps, SNR_est), '.');
    plot(samples + 1j*eps, '.');
    plot(samples(idx_err) + 1j*eps, '.');
    plot(samp_orig + 1j*eps, '+');
    title("Noise Comparison Constellation");
    if any(idx_err)
        legend("AWGN at SNR", "Measured", "In Error", "Ideal");
    else
        legend("AWGN at SNR", "Measured", "Ideal");
    end
    axis equal;

    % Show noise spectrum
    figure(106); clf; hold on;
    [f, s_n_meas] = singfourSAFE(time_samples, noise_voltage.^2);
    [~, s_n_awgn] = singfourSAFE(time_samples, (awgn(samp_orig, SNR_est) - samp_orig).^2);
    plot(f, abs(s_n_meas), f, abs(s_n_awgn));
    title("Noise Power Spectrum");
    xlabel("Frequency (Hz)");
    
    % Mark sample times on time-domain waveform
    figure(107); clf; hold on;
    plot(time_samples(~idx_err), real(samples(~idx_err)), 'o');
    plot(time_samples(~idx_err), imag(samples(~idx_err)), 'o');

    plot(time_samples(idx_err), real(samples(idx_err)), 'x');
    plot(time_samples(idx_err), imag(samples(idx_err)), 'x');
    

    title("Samples in Time Domain");
    if any(idx_err)
        legend("I channel", "Q channel", "I channel ERR", "Q channel ERR");
    else
        legend("I channel", "Q channel");
    end

    % Calculate and plot the impulse response of the channel.
    % If the equalizer is enables and working properly, the impulse
    % response should be an impulse function at t=0;
    measured_frame = samples(1:numel(original_sample_frame));
    original_frame = original_sample_frame;
    measured_frame = measured_frame/(sqrt(mean(abs(measured_frame).^2)));
    original_frame = original_frame/(sqrt(mean(abs(original_frame).^2)));

    scale = 1/numel(measured_frame);
    s_meas = scale*fftshift(fft(measured_frame));
    s_orig = scale*fftshift(fft(original_frame));
    s_filt = s_meas./s_orig;
    s_filt(isnan(s_filt) | isinf(s_filt)) = 0;
    
    ir = ifft(fftshift(s_filt)/scale);
    ir = ir/max(abs(ir));
    
    figure(204); clf; hold on;
    symboltime = time_samples(1:numel(ir));
    plot(symboltime, real(ir));
    plot(symboltime, imag(ir));
    title("Impulse Response");
    xlabel("Time (s)");
    legend("Real Part", "Imaginary Part");
end

end
