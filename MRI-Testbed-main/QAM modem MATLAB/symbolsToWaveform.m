function [time,waveform] = symbolsToWaveform(symbols, rate_sym, rate_samp, fc, bw, beta)
% symbolsToWaveform is the central function of Binary_To_QAM_Waveform.
% This function takes a vector of QAM symbol values, and returns a
% time-domain waveform sampled at the sepcified symbol rate and
% QAM-modulated according to the parameters below:

    % rate_samp is the sample rate.
    % rate_sym is the symbol rate.
    % fc is the center frequency.
    % bw is the bandwidth of the raised cosine filter.
    % beta is the rolloff of the raised cosine filter.

% Returns the upsampled waveform, and the corresponding time vector.

%% Set the sample rate
% Assume, for now, that the sample rate is an integer multiple of the
% symbol rate.
sps_int = ceil(rate_samp / rate_sym);

% Compute the minimum oversampling rate required to make sps an integer.
% Use this sample rate for the initial generation of the waveform.
rate_samp_int = sps_int*rate_sym;

%% Upsample the symbol sequence.
% The symbol sequence must be upsampled and possibly interpolated in order
% to match the desired symbol rate and sample rate.

% First, assume the number of samples per symbol is an integer.
% Note that if this assumption is wrong, we will oversample the data
% slightly, then interpolate the pulse-shaped data in a later step.

% Do time vector calculation based on symbol rate.
% Note that we want to preserve the time scale, not the actual sample rate,
% so the variables used here will produce the right start and end times.
% Version 1
tmax = (1/rate_sym)*(length(symbols)) - 1/rate_samp_int;
t_up_int = (0:(1/rate_samp_int):tmax)'; % Time step by sample period

% Upsample the data (zero-filling)
% set the phase to be as close to 50% as we can.
S2_upsampled = upsample(symbols, sps_int, floor(sps_int/2));


%% Build and apply the raised cosine filter
% singfourSAFE / invsignfourSAFE will eliminate the imaginary part of the 
% signal, so we have to split the signal into I and Q and work with each
% component individually, then recombine at the end.

% Split into I and Q channels
S2_I = real(S2_upsampled);
S2_Q = imag(S2_upsampled);

% Take the Fourier Transform (needed for cosine filtering)
%[f_S2, s_S2] = singfourSAFE(t_upsampled, S2_upsampled);
[f_S2, s_S2_I] = singfourSAFE(t_up_int, S2_I);
[~,    s_S2_Q] = singfourSAFE(t_up_int, S2_Q);

% Build the root-raised cosine filter
% center frequency, bandwidth, and rolloff are passed in as arguments.
s_rrcf = rrcf(f_S2, fc, bw, beta);

% Apply the RRCF
%s_S3 = s_S2.*(s_rrcf);
s_S3_I = s_S2_I.*(s_rrcf);
s_S3_Q = s_S2_Q.*(s_rrcf);

% IFFT back to time domain
%[~, S3_pulseshape] = invsingfourSAFE(f_S2, s_S3);
[~, S3_I] = invsingfourSAFE(f_S2, s_S3_I);
[~, S3_Q] = invsingfourSAFE(f_S2, s_S3_Q);

% Recombine I and Q channels
S3_pulseshape = S3_I + 1j*S3_Q;


%% Adjust for non-integer sample rate, if needed.
% It may be that the desired symbol rate and the sample rate are not clean
% integer multiples of one another.  If this is the case, we will need to
% interpolate the output waveform to achieve the desired final sample rate;
% this is handled by the code below (which has no effect if the final 
% samples per symbol is an integer).

t_interp = (0:(1/rate_samp):tmax)'; % Time step by final sample period

% Now, interpolate the pulse-shaped waveform.
waveform = interp1(t_up_int, S3_pulseshape, t_interp, 'makima');
time = t_interp;

% Plot interpolation comparison
%{
figure(101); clf; hold on;
    plot(t_up_int, S3_I);
    plot(t_up_int, S3_Q);
    plot(t_interp, real(waveform));
    plot(t_interp, imag(waveform));
mean(abs(S4_OUTPUT))
mean(abs(S3_pulseshape))
%}

% Plot continuity
%{
figure(102); clf; hold on;
    plot([S3_I; S3_I]);
    plot(S3_I);
shifted = circshift(S3_I, 1);
delta = (S3_I - shifted);
n_repeated_points = sum(delta == 0)
%}


end

