function [samples, markers, notes] = AWG_read(filename)
%% Documentation
% This function reads waveform data from the binary format used by the
% M8195A Arbitrary Waveform Generator.  Note that sampling frequency
% information is not naturally embedded in the file, so be careful that
% sampling frequency settings are synchronized between MATLAB and the AWG.
% However, it is possible to embed sampling frequency information into the
% file using the AWG_write function.  If such embedded notes exist, this
% function will return them as a character array.

% Returns:
% Samples: waveform samples as signed 8-bit integers.
% Markers: digitla markers as signed 8-bit integers.
% Notes: character vector of any embedded notes that may exist.

% Arguments:
% filename: path to the file, given as a string or char array.  By
% convention, AWG files end with a '.bin' extension.

% Waveforms are always saved in int16 format (values -32,768 to 32,767),
% but only the first 8 bytes are actual sample data.  The reamaining bytes
% are discarded, except the last two, which are used as markers.
% Thus, we read the data in as 8-bit integers, where every other integer is
% a sample, and the others are markers.

notes = '';
format = 'int8=>int8'; % Reads int8.
% See https://www.mathworks.com/help/matlab/ref/fread.html for info on how
% to set the precision (aka input/output format).

%% Open and read the file contents
[fileID,errmsg] = fopen(filename, 'r', 'ieee-le');
if fileID < 0 
   error(errmsg);
end

A = fread(fileID,format);

% Get the waveform samples
samples = A(2:2:end);

% Get the waveform markers
markers = bitand(int8(A(1:2:(end-1))), int8(3)); % Mask dead bits to get markers

% Get the deada bits (may contain notes)
deadbits = double(A(1:2:(end-1))); % Each value is 6 dead bits + 2 marker bits.

% Close the file
fclose(fileID);

%% Extract any embedded data in the waveform file
% deadbits may contain 6 bits of note information, shifted to fall within
% the acceptable value ranges of a signed 8-bit integer (-128 offset).
% Bits are shifted two places left, so we shift them back to the 6 LSBs.
deadbits = bitshift(deadbits + 128, -2);
bitbuffer = zeros(1, 6*length(deadbits)); % Maximum message size
for n = 1:1:length(deadbits)
    % Stuff the recovered data, 6 bits at a time, into a buffer.
    bitbuffer((1:6) + 6*(n-1)) = bitget(deadbits(n),6:-1:1);
end

% Reconstruct the original int8 characters froam the data in the buffer.
for n = 1:1:(length(bitbuffer)/8)
    
    % Grab 8 bits.
    charbits = fliplr(bitbuffer((1:8) + 8*(n-1)));
    
    % Get indicies of the bits to set.
    bitidx = find(charbits);
    
    % Get character code
    charcode = (sum(bitset(int8(0), bitidx)) + 0);
    
    % If the character is not alphanumeric, skip it.
    if (charcode >=0 ) && (charcode <= 31)
        continue;
        
    % Otherwise, accumulate it into the return string.
    else
        % Convert it to a character.
        notes = [notes, char(charcode)];
    end
    
end

end

%fprintf('\nNOTES:\n%s\n\n', notes);