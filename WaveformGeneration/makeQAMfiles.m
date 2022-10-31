clear variables;
    
%% User Settings
M = 4;
N = 4;
rate_sym = 10e9; %3.19997e9; % symbol rate
fc_original = 12.5e9;
beta = 0.9;
filepath = 'C:\Users\UTOL\Desktop\MRI-Testbed-main';
diagnostics_on = 1;
decode_on = 1;
plots_on = 1;
apply_transfer_function = 0;

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

if diagnostics_on
    fprintf("\nCarrier changed by %.4f%% (%.1f kHz).\n", 100*(fc-fc_original)/(fc_original),(fc-fc_original)/1e3);
    fprintf("Excess carrier cycles per symbol changed from %.3e to %.3e\n", mod((n_sym/rate_sym)*fc, 1), mod((1/rate_sym)*fc, 1));
    fprintf("Excess carrier cycles per waveform changed from %.3e to %.3e\n", mod((1/rate_sym)*fc, 1), mod((n_sym/rate_sym)*fc, 1));
end

%% Set the sample rate
% Set it so that there are an integer number of samples per waveform.
safety = 1 + beta; % bandwidth safety factor
rate_samp_min = ceil(max(2*(fc + (safety)*rate_sym/2), 54e9));
rate_samp_max = 65e9; % AWG upper limit

% Sample rate must be an integer multiple of: rate_sym/n_sym
% At least, it must be close.  Here, we set the sample rate to be an
% integer multiple of rate_sym/n_sym...
rate_samp = ceil(n_sym*rate_samp_min/rate_sym)*(rate_sym/n_sym);

% ... and here we round it to the nearest 10 kHz.  This puts the
% sample rate within the resolution of the M8195A signal generator.
rate_samp = (1e1)*round(rate_samp/(1e1));


%% Set the output filename.
symbol_filename = sprintf("M%iN%i.sym",M,N);
source_filename = sprintf("M%iN%i_%.2fGbd_%.1fGsps_%.2fBeta.mat",M,N,rate_sym/1e9,rate_samp/1e9,beta);
awg_filename = sprintf("M%iN%i_%.2fGbd_%.1fGsps_%.2fBeta",M,N,rate_sym/1e9,rate_samp/1e9,beta);

symbol_file = fullfile(filepath, symbol_filename);
source_file = fullfile(filepath, source_filename);
awg_file = fullfile(filepath, awg_filename);

%% Generate the symbol sequence and write it to a file.
file = fopen(symbol_file, 'W');
format = convertStringsToChars(sprintf("ubit%i",log2(M)));
fwrite(file, makeSymbolSequence(M,N), format);
fclose(file);

%% Read in the data
file = fopen(symbol_file);
symbols = fread(file, convertStringsToChars(sprintf("ubit%i",log2(M))));
fclose(file);

samples = qammod(symbols, M);
samples = samples(:);

n_symbols = length(samples);
n_bits = log2(M)*n_symbols;

%% Convert the data into a time-domain waveform at the sample rate

% Calculate spectral efficiency and bandwidth required.
% In the end, the bandwidth of the QAM link simplifies down to
% equal to the symbol rate, but I've kept the expanded math here
% for reference.
bits_per_symbol = log2(M);
%bit_rate = rate_sym*bits_per_symbol;
%spectral_efficiency = bits_per_symbol;  % bits/s per Hertz of bandwidth.

% If the desired throughput is B bits/s, then the necessary bandwidth is:
%bw = bit_rate/spectral_efficiency;
% Other is valid, bu this is easier.
bw = rate_sym;

[time,baseband] = symbolsToWaveform(samples, rate_sym, rate_samp, 0, bw, beta);
I = real(baseband);
Q = imag(baseband);

% Convert I and Q channels to real waveform
signal = I.*cos(2*pi*fc*time) + Q.*sin(2*pi*fc*time);

% Plot
%{
figure(100); clf; hold on;
    plot(time, signal);
    plot(time, I);
    plot(time, Q);
%}

%% Put important information into a struct
% This way it is easily accessed by the demodulation program.
original = struct;

original.modulation_order = M;
original.block_length = length(samples);
original.symbol_rate = rate_sym;

original.samples = samples;
original.sample_rate = rate_samp;
original.rcf_rolloff = beta;

original.fc = fc;

%original.time = time;
%original.signal = signal;

save(source_file, 'original')


%% SET IMPORTANT INFORMATION
% To Do: Generate notes programatically based on waveform property file.
% Currently, just define the notes manually here:
%notes = 'fs=40GHz, r_sym=5G/s, fc=12GHz, beta=0.35, RRCF.';
notes = sprintf('r_samp=%.2fG/s, r_sym=%.2fG/s, fc=%.2fGHz, beta=%.2f', rate_samp/1e9, rate_sym/1e9, fc/1e9, beta);

%% Make a signal, markers, and notes

% Signal
% NOTE:  The signal must be real.  If the signal is complicated to make, 
% it may be best to generate the signal in a seperate script, then use this
% file to save it.

% Load a previously-generated signal.
% This must load both a signal named "signal" and a time vector called "t".
% Optionally (and optimally) this will also load the sample rate "fs" to
% overwrite the one previously defined.
 load(source_file);

%% Extract and set useful information
fs = original.sample_rate;
%time = original.time;
%signal = original.signal;

%% Generate Markers
% Markers are 2 bit values (channel 1 and 2), so must be integers between 
% 0 and 3 inclusive.
markers = zeros(1, length(signal))';
markers(1:min(10, round(length(signal)/2))) = 1; % mark the beginning of the waveform.
%markers(1:64*512:end) = markers(1:64*512:end) + 2;
%}

%% If the signal is complex, convert it to a real-valued signal.

%% Write the file
AWG_write_CSV(signal, markers, notes, awg_file, rate_samp, 1);
scaled = AWG_write_BIN(signal, markers, notes, awg_file, 1);
%% Read the file back and compare the original and digitized copies
[s, m, n] = AWG_read_BIN(awg_file);

if plots_on
    % Print out the notes.
    fprintf('NOTES:\n%s\n\n',n);

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
        %warning('off','legend:Ignoring extra legend entries.');
        legend('original', 'digitized', 'm1', 'm2', 'textcolor', [.9, .9, .9])

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

if decode_on
    symbols_to_drop = 1000;
    frames = 100;
    scope_fs = 80e9;

    ts = 1/scope_fs;
    dt = time(2) - time(1);
    t_end = (frames*n_sym*1/rate_sym);
    
    testsignal = repmat(signal, frames, 1);
    signal_time = 0:(dt):(t_end);
    signal_time = signal_time(1:length(testsignal));
    
    scope_sample_times = (ts):(ts):(t_end);
    scope_sampled_signal = interp1(signal_time, testsignal, ...
        scope_sample_times, 'spline');

    if apply_transfer_function
        incident_angle = 0;
        polarization = 'S';

        upconverter_n = 12;
        f_mixer = 25e9;
        f_shift = f_mixer*upconverter_n; % Upper Sideband
        [f, S] = singfourSAFE(scope_sample_times, scope_sampled_signal);
        f_stack = f + f_shift;
        
        % Silicon slab
        % slab is 4 mm thick.
        thicknesses = [0, 4e-3, 0];
        indicies = [1, 1, 1]; % Index of Si is 3.418
        stack = [thicknesses(:), indicies(:)];
        
        
        [S11, S21] = MakeStackAngle2(f_stack, stack, ...
            incident_angle, polarization);

        I = real(S).*S21;
        Q = imag(S).*S21;

        [trash, I] = invsingfourSAFE(f, I);
        [~, Q] = invsingfourSAFE(f, Q);
        scope_sampled_signal = I - 1j*Q;

        S11_angle = unwrap(10*angle(S11))/10;

        % Plot the stack's transfer function
        S21_angle = unwrap(10*angle(S21))/10;
        
        S11_gd = derivative(2*pi*f_stack, S11_angle);
        S21_gd = derivative(2*pi*f_stack, S21_angle);
        
        if plots_on
            figure(11); clf; hold on;
            plot(f_stack/1e9, 10*log10(abs(S11)), f_stack/1e9, 10*log10(abs(S21)));
            %ylim([-20, 0]);
            xlabel("Frequency (GHz)");
            ylabel("dB");
            legend("S11", "S21");
            title("Magnitude");
            xlim((f_shift + [0, rate_samp/2])/1e9);
            
            figure(12); clf; hold on;
            plot(f_stack/1e9, S11_gd);
            plot(f_stack/1e9, S21_gd);
            %ylim([-20, 0]);
            xlabel("Frequency (GHz)");
            ylabel("group delay (s^{-1})");
            legend("S11", "S21");
            title("Group Delay");
            xlim((f_shift + [0, rate_samp/2])/1e9);
    
            figure(13); clf; hold on;
            [xplot, yplot] = singfourSAFE(trash, scope_sampled_signal);
            plot(xplot/1e9, 20*log10(abs(yplot)));
            xlim([0, rate_samp/(2*1e9)]);
        end
    end
    tic
    [~, nsym, errors, SNR] = processQAM(...
        original.modulation_order, original.block_length,...
        original.symbol_rate, original.fc, symbols_to_drop, ...
        original.rcf_rolloff, original.samples, ...
        80e9, scope_sampled_signal, 1, 1);
    toc

    fprintf("\n%i symbols sent.", nsym);
    fprintf("\nProcessed %i symbols/s.", round(nsym/toc));
    fprintf("\nSNR is %.2f", SNR);
    fprintf("\nSER is %f", errors.sym/nsym);
    fprintf("\nBER is %f\n", errors.bit/(nsym*log2(original.modulation_order)));
end