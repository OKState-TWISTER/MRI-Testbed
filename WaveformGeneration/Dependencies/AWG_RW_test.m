%% Set the file path
%filename_source = 'name_of_signal_file.mat';
filename_destination = '1GHz_cosine.bin';

% Notes
notes = 'default notes';

%% Define the sampling rate (IMPORTANT)
fs = 64.0e9;

%% Make a signal, markers, and notes

% Signal
% NOTE:  The signal must be real.  If the signal is complicated to make, 
% it may be best to generate the signal in a seperate script, then use this
% file to save it.

% Load previously-generated signal.
% load(filename_source);

% Or use this dummy signal.
fc = 1e9; % Carrier frequency of 1 GHz.
tmax = 10/fc - 1/fs; % Drop a single sample so the waveform can be repeated.
t = (0:(1/fs):tmax)'; % Time goes from zero to tmax at sample rate fs.
phi0 = 0;
signal = 127*cos(2*pi*fc*t + phi0);

% Markers
% Markers are 2 bit values (channel 1 and 2), so must be integers between 
% 0 and 3 inclusive.
spacing1 = 1/fc;
markers = zeros(1, length(signal))';

% Uncomment and modify these if you want to include markers.
%markers(1:8:end) = 1; % Marker Ch. 1
%markers(1:(fs/fc):end) = markers(1:(fs/fc):end) + 2;  % Marker Ch. 2

%% Write the file
AWG_write(signal, markers, notes, filename_destination, 1);

clearvars -except filename_destination t signal markers

%% Read the file back and compare the original and digitized copies
[s, m, n] = AWG_read(filename_destination);

% Print out the notes.
fprintf('NOTES:\n%s\n\n',n);

% Plot time-domain
figure(1); clf; hold on;
s1 = signal;
s2 = double(s);
plot(t, s1)
plot(t, s2);
xlabel('Time');
ylabel('Normalized Amplitude');
title('Time Domain');
legend('original', 'digitized', 'textcolor', [.9, .9, .9])

% If markers are used, plot markers.
if (sum(markers) ~= 0) || any(markers ~= m, 'all')
    figure(1); hold on;
    m1 = bitand(uint8(markers), uint8(1)) ~= 0;
    m2 = bitand(uint8(markers), uint8(2)) ~= 0;
    plot(t(m1), s2(m1), 'x');
    plot(t(m2), s2(m2), 'o');
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
[f1, S1] = singfourSAFE(t, s1);
[f2, S2] = singfourSAFE(t, s2);
f1 = f1'; f2 = f2';
S1dB = 20*log10(abs(S1 + eps)); S2dB = 20*log10(abs(S2 + eps));
plot(f1, S1dB);
plot(f2, S2dB);
xlim([0, f1(end)/2])
xlabel('Frequency (Hz)')
ylabel('Spectral Power (dB)')
title('Frequency Domain')
legend('original', 'digitized', 'textcolor', [.9, .9, .9])


% Plot 8-bit precision reduction error (time-domain)
figure(4); clf; hold on;
s3 = (s1 - s2);
plot(t, s3);
xlabel('Time');
ylabel('Digitization Error');
title('ERROR: Time Domain');
legend('8bit precision error', 'textcolor', [.9, .9, .9])

% Plot 8-bit precision reduction error (frequency domain)
figure(5); clf; hold on;
[f3, S3] = singfourSAFE(t, s3);
f3 = f3';
S3dB = 20*log10(abs(S3 + eps));
plot(f3, S3dB);
xlim([0, f1(end)/2])
xlabel('Frequency (Hz)')
ylabel('Spectral Power (dB)')
title('ERROR: Frequency Domain')
legend('8bit precision error', 'textcolor', [.9, .9, .9])