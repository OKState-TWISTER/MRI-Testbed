clear variables
% This script attempts to demodulate a QAM signal captured by the DSO and 
% prints out the symbol error rate, estimated SNR, and the recovered data.
% The script prints out these statistics and, if an output filename is 
% provided, will write the recovered binary data into that file.
diagnostics_on = 0;

%% IMPORTANT SETTINGS
IF_estimate = 1.6e9;  % Estimated IF, in Hz.
sym_to_drop = 300; % Number of early (erronious) symbols to drop.


%% LOAD THE CAPTURE DATA and SET WORKSPACE VARIABLES
% Set the filenames, either manually or interactivly (if default is blank).

% This is the file put out by generateQAM.m
filename_original = '';
while isempty(filename_original)
    filename_original = input('Enter the original filename: ', 's');
end

% This is the file captured by the DSO.
filename_capture = '';
while isempty(filename_capture)
    filename_capture = input('Enter the capture filename: ', 's');
end

% The file to write the data to, if any.
filename_output = input('Enter the output filename (hit enter to skip): ', 's');
fprintf('\n');

% This original file should contain a structure, 'original', which contains
% all the original settings for the transmitted signal.
load(filename_original);

% This file is a .mat file off the DSO.  It is assumed that Channel 1
% contains the time-domain data.
load(filename_capture);

%% CREATE A STRUCTURE CONTAINING ALL SIGNALS AND SETTINGS
waveform = struct;

% This block of settings was previously loaded from filename_original
waveform.original = original;

% Assume that all capture settings are identical to the original ones.
waveform.capture = waveform.original;

% Now, adjust any capture settings that are different.
waveform.capture.sample_rate = 1/Channel_1.XInc; % Oscilloscope sample rate.
waveform.capture.local_oscillator_frequency = IF_estimate;
waveform.capture.signal = (double(Channel_1.Data));
waveform.capture.symbols_to_drop = sym_to_drop;

M = waveform.capture.modulation_order;

%% Process the waveform
[data, nsym, errors, SNR] = processQAM(waveform, diagnostics_on);

%% Do additional analysis on the results

% Theoretical SER for the calculated SNR, ASSUMING GAUSSIAN NOISE.
% The assumption of Gaussian noise may not always be correct, so verify.
% NOTE:  For QPSK only.
SER_theory = erfc(sqrt(0.5*(10.^(SNR/10)))) - (1/4)*(erfc(sqrt(0.5*(10.^(SNR/10))))).^2;


%% PRINT RESULTS
fprintf("\nAnalyzing %.0d symbols:\n", nsym);
fprintf("SNR is %.2f dB\n", SNR);
fprintf("Observed BER is %.2g (%.0f bits)\n", errors.bit/(nsym*log2(M)), errors.bit);
fprintf("Observed SER is %.2g (%.0f symbols)\n", errors.sim/nsym, errors.sim);
% For QPSK only:
fprintf("Predicted QPSK SER is %.2g (%.0f symbols)\n", SER_theory, round(SER_theory*nsym));
fprintf("\n")

%% Write the data back out to a file (experimental)
if ~isempty(filename_output)
    block_length = waveform.capture.block_length;
    file = fopen(filename_output, 'W');
    format = convertStringsToChars(sprintf("ubit%i",log2(M)));
    fwrite(file, data.symbols(1:block_length), format);
    fclose(file);
end
