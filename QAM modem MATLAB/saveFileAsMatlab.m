function [data, nsym, errors, SNR_est, SNR_raw] = saveFileAsMatlab(filename, M, block_length, symbol_rate, fc, symbols_to_drop, rcf_rolloff, original_sample_frame, rate_samp, captured_samples, diagnostics_on, eq_on)

fprintf("\nHELLO, WORLD!")

filepath = "C:\Users\kstreck\Desktop\matlabtestfiles";
filepath = fullfile(filepath, filename);
save(filepath, "M", "block_length", "symbol_rate", "fc", "symbols_to_drop", "rcf_rolloff", "original_sample_frame", "rate_samp", "captured_samples", "diagnostics_on", "eq_on");

data = 1;
nsym = 1;
errors = struct();
    errors.bit = 1;
    errors.sym = 1;
SNR_est = 1;
SNR_raw = 1;

end