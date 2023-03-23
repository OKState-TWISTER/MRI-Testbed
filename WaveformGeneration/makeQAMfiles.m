function [out] = makeQAMfiles_current(varargin)
profile on
if isempty(dbstack(1))
    M = 4;
    N = 4;
    rate_sym = 10e9;
    fc_original = 12.5e9;
    beta = 0.9;
    filepath = "C:\Users\kstreck\Desktop\Waveforms";
    apply_transfer_function = 0;
    decode_on = 1;
    diagnostics_on = 1;
    eq_on = 1;

else
    in = varargin{1};
    M = in.M;
    N = in.N;
    rate_sym = in.rate_sym;
    fc_original = in.fc;
    beta = in.beta;
    filepath = in.filepath;
    diagnostics_on = in.diagnostics_on;
    decode_on = in.decode_on;
    apply_transfer_function = in.apply_transfer_function;
    eq_on = in.eq_on;
end


%% Tweaking the carrier frequency
% Adjust this so that we get an integer number of carrier cycles over the
% durstion of the waveform
n_sym = N*(M^N);
carrier_cycles = (n_sym*(1/rate_sym))*fc_original;
extra_cycles = mod(carrier_cycles, 1);
if extra_cycles < 0.5
    % Decrease fc
    fc = fc_original*(1 - (extra_cycles/carrier_cycles));
else
    % Increase fc
    fc = fc_original*(1 + ((1-extra_cycles)/carrier_cycles));
end

%% Set the sample rate
% Set it so that the number of samples per waveform is a multiple of 256,
% while observing Nyquist limits, etc.
excess_bw = 1 + beta;
rate_samp_min = ceil(max(2*(fc + (excess_bw)*rate_sym/2), 54e9));
rate_samp = getAWGsamplerate(n_sym/rate_sym, rate_samp_min, 1);

% ... and here we round it to the nearest 10 Hz.  This puts the
% sample rate within the resolution of the M8195A signal generator.
rate_samp = (1e1)*round(rate_samp/(1e1));


%% Set the output filename.
source_filename = sprintf("M%iN%i_%.2fGbd_%.1fGsps_%.2fBeta.mat",M,N,rate_sym/1e9,rate_samp/1e9,beta);
awg_filename = sprintf("M%iN%i_%.2fGbd_%.1fGsps_%.2fBeta",M,N,rate_sym/1e9,rate_samp/1e9,beta);

source_file = fullfile(filepath, source_filename);
awg_file = fullfile(filepath, awg_filename);

%% Make the symbol sequence
samples = qammod(makeSymbolSequence(M,N), M);
samples = samples(:);



%% MULTIPATH INTERFERENCE - FOR EQ TESTING AND DEBUG (delete this later)
originalsamples = samples;

%{
W = [0,0,0,1,0,.08,0];
reftap = 4;

pad = zeros(numel(W), 1);
%pad = samples(1:numel(W));

samples = [pad; samples; pad];
samples = circshift(filter((W),1,samples), -(numel(W) + reftap -1)); % Has padding on both ends.
samples = samples(1:(end-2*numel(W)));  %Remove the padding
%}


%% Convert the data into a time-domain waveform at the sample rate
bw = rate_sym;

[time,baseband] = symbolsToWaveform(samples, rate_sym, rate_samp, 0, bw, beta);
time = time(:);
I = real(baseband);
Q = imag(baseband);

% Convert I and Q channels to real waveform
phase_shift = pi/2 + pi/90 + pi/4;
signal = I.*cos(2*pi*fc*time + phase_shift) + Q.*sin(2*pi*fc*time + phase_shift);


%% APPLY TRANSFER FUNCTION
if apply_transfer_function
    warning("Applying a transfer function is not currently safe; please rewrite this code using verified Fourier transform process.")
    % Mixer shifts 0 Hz to fc_thz
    fc_thz = 365e9;
    upconverter_n = 12;
    f_mixer = fc_thz / upconverter_n;

    % Shift the signal up to THz frequencies.
    % Note: signal is below the Nyquist limit, but within the Nyquist
    % bandwidth.  We'll shift the frequency up after the Fourier transform
    % in the next step.
    signal_thz = signal;%.*exp(1j*2*pi*fc_thz*time);
    [f, S] = singfourSAFE(time, signal_thz);
        f = f + (fc_thz - 2*fc);  % Account for ailasing.
        S = [S((round(length(S)/2) + 1):end), S(1:(round(length(S)/2)))];
        S = S(:);


            % Dielectric Slab
            %{
            incident_angle = 0;
            polarization = 'S';

            thicknesses = [0, 7e-3, 0];
            indicies = [1, 5.418, 1]; % Index of Si is 3.418
            stack = [thicknesses(:), indicies(:)];
            
            [S11, S21] = MakeStackAngle2(f, stack, ...
                incident_angle, polarization);
            %}

            % Atmosphere
            
            distance = 30; % m
            rho = 13.79; % grams per cubic meter (70% RH @ 22 deg.)
            T = 22.22; % 72 F
            S21 = atmospheric_attenuation(f, distance, rho, T);
            %}

            %S21 = ones(size(S21)).*exp(-j*2*pi*f*200e-10);

            S21 = S21(:);
            %S11 = S11(:);
            S = S.*S21;
            halfway = round(length(S)/2);
            %S(1:halfway) = S(1:halfway);
            %S((halfway+1):end) = 0;
            if diagnostics_on
            figure(901); clf; hold on;
            plot(f/1e9, 20*log10(abs(S21)));
            plot(f/1e9, 20*log10(abs(S)));
            end
    
            f = f - (fc_thz - 2*fc);  % Account for ailasing.
            S = [S((round(length(S)/2) + 1):end), S(1:(round(length(S)/2)))];
            S = S(:);

    [~, signal_thz] = invsingfourSAFE(f, S);
    signal = signal_thz;%.*exp(1j*2*pi*fc_thz*time);
    
    % Finally, chop off the "negative" frequencies to get a real signal.
    [f, S] = singfourSAFE(time, signal);
        S(1:halfway) = S(1:halfway);
        S((halfway+1):end) = 0;
        if diagnostics_on
        figure(988); clf;
        plot(f, 10*log10(abs(S)));
        end
    [~, signal] = invsingfourSAFE(f, S);

end


%% Put important information into a struct
% This way it is easily accessed by the demodulation program.
original = struct;
original.modulation_order = M;
original.block_length = length(samples);
original.symbol_rate = rate_sym;
original.samples = originalsamples;
original.sample_rate = rate_samp;
original.rcf_rolloff = beta;
original.fc = fc;


%% SET NOTES
% To Do: Generate notes programatically based on waveform property file.
% Currently, just define the notes manually here:
%notes = sprintf('r_samp=%.2fG/s, r_sym=%.2fG/s, fc=%.2fGHz, beta=%.2f', rate_samp/1e9, rate_sym/1e9, fc/1e9, beta);
notes = '';


%% Generate Markers
% Markers are 2 bit values (channel 1 and 2), so must be integers between 
% 0 and 3 inclusive.
markers = zeros(1, length(signal))';
markers(1:min(10, round(length(signal)/2))) = 1; % mark the beginning of the waveform.
%markers(1:64*512:end) = markers(1:64*512:end) + 2;
%}


%% SAVE THE FILES
save(source_file, 'original');
%AWG_write_CSV(signal, markers, notes, awg_file, rate_samp, 1);
scaled = AWG_write_BIN(signal, markers, notes, awg_file, 1);


%% Read the file back and compare the original and digitized copies
[s, m, n] = AWG_read_BIN(awg_file);
if mod(length(s), 256) ~= 0
    warning("Signal length (%i) is not a mutiple of 256!", length(s));
end


%% DIAGNOSTICS  ===========================================================

if diagnostics_on
    % Print out the notes.
    %fprintf('NOTES:\n%s\n\n',n);

    % Plot time-domain
    figure(1); clf; hold on;
    s1 = scaled;
    s2 = double(s);
    plot(time, s1)
    plot(time, s2);
    xlabel('Time');
    ylabel('Normalized Amplitude');
    title('Time Domain');
    legend('original', 'digitized', 'textcolor', [.9, .9, .9])

    % If markers are used, plot markers.
    if (sum(markers) ~= 0) || any(markers ~= m, 'all')
        figure(1); hold on;   
        m1 = bitand(uint8(markers), uint8(1)) ~= 0;
        m2 = bitand(uint8(markers), uint8(2)) ~= 0;
        plot(time(m1), s2(m1), 'x');
        plot(time(m2), s2(m2), 'o');
        warning('off', 'MATLAB:legend:IgnoringExtraEntries')
        legend('original', 'digitized', 'm1', 'm2', 'textcolor', [.9, .9, .9])
        warning('on', 'MATLAB:legend:IgnoringExtraEntries')
        %{
        figure(3); clf; hold on;
        plot(t, markers);
        xlabel('Time')
        ylabel('Spectral Power (dB)')
        title('Digital Markers')
        %}
    end

    % Plot frequency-domain.
    figure(2); clf; hold on;
    [f1, S1] = singfourSAFE(time, s1);
    [f2, S2] = singfourSAFE(time, s2);
    f1 = f1'; f2 = f2';
    S1dB = 20*log10(abs(S1 + eps)); S2dB = 20*log10(abs(S2 + eps));
    plot(f1/1e9, S1dB);
    plot(f2/1e9, S2dB);
    xlim([0, f1(end)/(2*1e9)])
    xlabel('Frequency (GHz)')
    ylabel('Spectral Power (dB)')
    title('Frequency Domain')
    legend('original', 'digitized', 'textcolor', [.9, .9, .9])

    % Plot 8-bit precision reduction error (time-domain)
    figure(3); clf; hold on;
    s3 = (s1 - s2);
    plot(time, s3);
    xlabel('Time');
    ylabel('Digitization Error');
    title('ERROR: Time Domain');
    legend('8bit precision error', 'textcolor', [.9, .9, .9])

    % Plot 8-bit precision reduction error (frequency domain)
    figure(4); clf; hold on;
    [f3, S3] = singfourSAFE(time, s3);
    f3 = f3';
    S3dB = 20*log10(abs(S3 + eps));
    plot(f3, S3dB);
    xlim([0, f1(end)/2])
    xlabel('Frequency (Hz)')
    ylabel('Spectral Power (dB)')
    title('ERROR: Frequency Domain')
    legend('8bit precision error', 'textcolor', [.9, .9, .9])
end


out = struct();
out.rate_samp = rate_samp;
out.fc = fc;
%profile report
%profile off


if decode_on
    frames = 50;
    scope_fs = 80e9;
    t_end = ((frames*n_sym*1)/rate_sym);
    testsignal = repmat(signal, frames, 1);
    signal_time = 0:(1/rate_samp):(t_end - 1/rate_samp);
    %signal_time = 0:(1/rate_samp):(t_end*2);
    %    signal_time = signal_time(1:numel(testsignal));
    scope_sample_times = (0):(1/scope_fs):(t_end - 50/scope_fs);
    %scope_sample_times = (0):(1/scope_fs):(t_end);

    scope_sampled_signal = interp1(signal_time, testsignal, ...
        scope_sample_times, 'spline');

    %sigPower = sum(abs(scope_sampled_signal(:)).^2)/numel(scope_sampled_signal); % In Watts
    %scope_sampled_signal = awgn(scope_sampled_signal, 10, 'measured', 'db');

    %{
    dfe = comm.DecisionFeedbackEqualizer('Algorithm','LMS', ...
    'NumForwardTaps',30,'NumFeedbackTaps',5,'StepSize',0.03);
    dfe.ReferenceTap = 3;
    dfe.Constellation = qammod((1:M)-1, M) + 1j*eps;
    dfe.WeightUpdatePeriod = 1000;
    %}

    dfe = comm.DecisionFeedbackEqualizer('Algorithm','LMS', ...
    'NumForwardTaps',4,'NumFeedbackTaps',3,'StepSize',0.03);
    dfe.ReferenceTap = 4;
    dfe.Constellation = qammod((1:M)-1, M) + 1j*eps;
    dfe.WeightUpdatePeriod = 1000;


%{
load("trash_eq_weights");
dfe = previousweights;
%}

    tic
    [data, nsym, errors, SNR_est, SNR_raw, weights] = processQAM(...
        original.modulation_order, original.block_length,...
        original.symbol_rate, original.fc, ...
        original.rcf_rolloff, original.samples, ...
        scope_fs, scope_sampled_signal, diagnostics_on, dfe);
    toc

    %
previousweights = weights;
previousweights(dfe.ReferenceTap) = 1;
save("trash_eq_weights", "previousweights");
    %}

    fprintf("\n%i symbols sent.", nsym);
    fprintf("\nProcessed %i symbols/s.", round(nsym/toc));
    fprintf("\nRaw  SNR is %.2f", SNR_raw);
    fprintf("\nEst. SNR is %.2f", SNR_est);
    fprintf("\nSER is %f", errors.sym/nsym);
    fprintf("\nBER is %f\n", errors.bit/(nsym*log2(original.modulation_order)));
end