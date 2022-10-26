function [S3_return] = makeSymbolSequence(M,N)
%% Makes a QAM symbol sequence that contains every permutation of length N.
% The input M is the QAM order (a power of 2): 2, 4, 16, 64, etc, equal to
% the number of symbols on the constellation diagram.

    %n_permutations = M^N;
    %n_symbols = N*n_permutations;
    %n_bits = log2(M)*n_symbols;

    % Generate each possible bit sequence
    %ideal_symbols = (qammod((0:M-1), M, 'UnitAveragePower',false));
    ideal_symbols = (0:M-1);
    S1_symbol_list = permn(ideal_symbols, N)';
    S2_linear = S1_symbol_list(:);
    
    S3_return = S2_linear;
end