function [out] = getAWGsamplerate(signal_duration, rs_min_signal, enforce_sample_rate)

rs_min_AWG = 54e9; % AWG lower limit
rs_max_AWG = 65e9; % AWG upper limit
dac_gran = 256; % DAC granularity.

% NOTE:  Duration should be equal to the last value in the time vector for
% a signal that starts on the first sample.

%% Set the sample rate
% Set it so that there are an integer number of samples per waveform.
rate_samp_min = max(rs_min_AWG, rs_min_signal);

% There must be an integer number of sample per waveform duration, AND the
% number of samples must be a multiple of the AWG's DAC granularity.
n_samp_min = dac_gran*ceil(rate_samp_min*signal_duration/dac_gran);
rate_samp = (n_samp_min) / signal_duration;

if (rate_samp > rs_max_AWG) && enforce_sample_rate
    error("Waveform could not be synthisized; required sample rate is greater than 65 G/s!");
end

out = rate_samp;