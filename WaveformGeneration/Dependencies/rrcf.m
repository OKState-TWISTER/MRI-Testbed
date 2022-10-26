function [RRCF] = rrcf(f, fc, bw, beta)
%UNTITLED2 Summary of this function goes here
%   Detailed explanation goes here
    % MODEL
    %(M) Generate the RCF.
    ff = f-fc;
    Ts = 1/bw;
    range_a = (abs(ff) <= (1-beta)/(2*Ts));
    range_b = ((1-beta)/(2*Ts) < abs(ff)) & (abs(ff) <= (1+beta)/(2*Ts));
    RCF = zeros(size(ff));
    RCF(range_a) = 1;
    RCF(range_b) = 0.5*(1 + cos((pi*Ts/beta)*(abs(ff(range_b))-(1-beta)/(2*Ts))));
    RRCF = sqrt(RCF);
    RRCF = RRCF(:);
end

