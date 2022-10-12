clear variables
% This script reads a file as binary data and converts it into a 
% time-domain QAM waveform.  Parameters in the file may be altered to set 
% the modulation order, symbol rate, center frequency, RCF rolloff factor,
% and sampling rate.
% This script outputs a .mat file containing the time domain waveform, 
% integer symbol sequence, and all relevant parameters. Make sure this file
% is on the MATLAB path; it will be used by the other QAM read/write files.

%% DEFINE IMPORTANT QAM PARAMETERS
M = 4; % Number of symbols on constellation diagram.
rate_samp = 64e9; % sample rate
rate_sym = 1e9; % symbol rate
fc = 4e9;
beta = 0.99;
% NOTE: Sample rate does not have to be a multiple of symbol rate, but this
% will result in interpolation later on to achieve the desired final sample
% rate.

%% Get input/output filenames
filename_in = '';
while length(filename_in) < 1
    filename_in = input('Enter the filename of the source data: ', 's');
end
%fprintf('\n');

% Set the output filename.
% This will be read by both AWG_write_with_analysis.m and QAM_analysis.m
filename_out = '';
while length(filename_out) < 1
    filename_out = input('Enter a waveform output filename: ', 's');
end
%fprintf('\n');

%{
while (mod(log2(M),1) ~= 0) || M < 2 % must be a power of two 2 or greater.
    M = input('Enter the QAM order (2, 4, 16, 64, etc): ');
end
%fprintf('\n');
%}

%{
N = 5; % Number of symbols per permutation sequence.
samples = makeSymbolSequence(M, N);
file = fopen('PermutationSequence', 'W');
fwrite(file, samples, 'ubit2');
fclose(file);
%}

%% Read in the data
file = fopen(filename_in);
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
bit_rate = rate_sym*bits_per_symbol;
spectral_efficiency = bits_per_symbol;  % bits/s per Hertz of bandwidth.

% If the desired throughput is B bits/s, then the necessary bandwidth is:
bw = bit_rate/spectral_efficiency;

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

original.time = time;
original.signal = signal;

save(filename_out, 'original')

% Run QAM_Waveform_To_AWG to write this waveform to a binary file.
