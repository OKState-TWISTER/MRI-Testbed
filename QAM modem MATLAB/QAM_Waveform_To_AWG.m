clear variables
% This script reads the file output by Binary_To_QAM_Waveform.m and does
% the bit-banging to write the waveform in the binary format required by 
% the AWG. This program can also place digital markers on the waveform and
% can insert custom notes into otherwise unused bits within the AWG
% waveform file.
% This script outputs a .bin file which can be loaded and run by the AWG.
% Note that the AWG will output this waveform on channel 1, with digital 
% markers on channels 3 and 4.
diagnostics_on = 0;

%% SET IMPORTANT INFORMATION

% Set the file paths
% This is the file put out by generateQAM.m (the original waveform)
filename_in = '';
while length(filename_in) < 1
    filename_in = input('Enter the waveform filename: ', 's');
end
fprintf('\n');

% This is the file you intend to transfer to the AWG.
filename_out = '';
while length(filename_out) < 1
    filename_out = input('Enter the output filename: ', 's');
end
fprintf('\n');

% To Do: Generate notes programatically based on waveform property file.
% Currently, just define the notes manually here:
notes = 'fs=64GHz, r_sym=1G/s, fc=4GHz, beta=0.99, RRCF.  Test signal for AWG SNRvsBER characterization.';

%filename_source = 'waveform.mat';
%filename_destination = 'QPSKtest4.bin';

%% Make a signal, markers, and notes

% Signal
% NOTE:  The signal must be real.  If the signal is complicated to make, 
% it may be best to generate the signal in a seperate script, then use this
% file to save it.

% Load a previously-generated signal.
% This must load both a signal named "signal" and a time vector called "t".
% Optionally (and optimally) this will also load the sample rate "fs" to
% overwrite the one previously defined.
 load(filename_in);

% Or load from a previously read waveform (.bin) file
%{
[signal, markers, notes] = AWG_read('RFat10G.bin');
signal = double(signal);

tmax = (1/fs)*(length(signal) - 1); % -1 avoids fencepost error
t = (0:(1/fs):tmax)'; % Time goes from zero to tmax at sample rate fs.
%}

%% Extract and set useful information
fs = original.sample_rate;
t = original.time;
signal = original.signal;

%% Generate Markers
% Markers are 2 bit values (channel 1 and 2), so must be integers between 
% 0 and 3 inclusive.
markers = zeros(1, length(signal))';
markers(1) = 1; % mark the beginning of the waveform.
%markers(1:64*512:end) = markers(1:64*512:end) + 2;
%}

%% If the signal is complex, convert it to a real-valued signal.


%% Write the file
scaled = AWG_write(signal, markers, notes, filename_out, 1);


%% Read the file back and compare the original and digitized copies
[s, m, n] = AWG_read(filename_out);

if diagnostics_on
    % Print out the notes.
    fprintf('NOTES:\n%s\n\n',n);

    % Plot time-domain
    figure(1); clf; hold on;
    s1 = scaled;
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
end