function [scaled] = AWG_write_BIN(samples, markers, notes, filename, autoscale)
%% Documentation
% This function - predictably - writes waveform data into a binary format
% that can be read by the M8195A Arbitrary Waveform Generator

% Returns:
% The scaled waveform that was written to the file.  The point of the
% function is to write out a file, so this return value can usually be
% discarded unless you're doing diagnostic stuff.

% Arguments:
% Samples: waveform samples.  These will be cast to 8-bit signed integers 
% after apropriate shifting and scaling, and must be real-valued.
% Markers: digital markers as signed 8-bit integers, between the values of
% 0 and 3 (00 and 11).  Each bit represents one of two channels.
% Notes: character vector of any embedded notes that should be stored in
% the dead bits of the binary file.  The length of the notes 
% (in 8-bit characters) must be less than or equal to 6/8 the length of the
% sample vector (in 8-bit samples).
% filename: path to the output file, given as a string or char array.  By
% convention, AWG files end with a '.bin' extension.
% autoscale:  Boolean value.  If true, scale the waveform for maximum
% dynamic range while maintaining zero-mean.  Unless you know exactly what
% you're doing, this should be true.

% Waveforms are always saved in int16 format (values -32,768 to 32,767),
% but only the first 8 bytes are actual sample data.  The reamaining bytes
% are discarded, except the last two, which are used as markers.
% Thus, we read the data in as 8-bit integers, where every other integer is
% a sample, and the others are markers.

% Sample rate is not specified in the binary file, so BE CAREFUL to ensure
% that the sample rate defined in the waveform read / write scripts matches
% the sample rate setting on the AWG.
% 64 Gsamples/s is the default sample rate.

format = 'int16'; 

%% Keepin' it real
% Samples should be a strictly real signal.

%% Scaling and digitization
% Scaling can be done internally on the AWG, but it's good form to do it
% here.
if autoscale
    % Set to zero mean.
    samples = samples - mean(samples);
    % Scale for maximum dynamic range
    samples = samples*(127/max(abs(samples)));
    scaled = samples;
end


%% Markers
% If ya want markers, now's the time to stick 'em in.
% Markes must be 2 bits or less - decimal three or below.
if (max(markers) > 3) || (min(markers) < 0)
    error("Marker resolution is only two bits - markers must be between 0 and 3.")
end

%% Inserting notes
% Insert extra note data into the 6 dead bits of each marker byte.

% First, make sure the notes will fit in the space available.
extra = 6*length(markers) - 8*length(notes);
if extra < 0
    notes = notes(1:(end-ceil(-extra/8)));
    fprintf("WARNING: your notes are too long; they have been truncated.\n");
end

bits = zeros(1, 6*length(markers));

for n = 1:1:length(notes)
    % bitget normally reads LSB first; go from 8 to 1 to reverse.
    bits((1:8) + 8*(n-1)) = bitget(uint8(notes(n)),8:-1:1);
end
% At this point, we've grabbed the bits in MSB format.
% Each block of 8 bits in data is a byte, MSB has lowest index.

% Put 6 bits at a time into an int8 with the two LSB masked to zero.
for n = 1:1:(length(bits)/6)
    % Grab 6 bits.
    subvector = fliplr(bits((1:6) + 6*(n-1)));
    
    % Get indicies of the bits to set.
    idx = find(subvector);
    
    % Convert the binary array values into an actual number (int8).
    unit = bitshift(sum(bitset(int8(0), idx)), 2) - 128;
    
    % Shift it all up by two places and store.
    markers(n) = bitor(int8(markers(n)), int8(unit));
end

%figure(10); clf; hold on;
%plot(markers);

%% Combine samples and markers (int8) into single stream (int16)
data = int8(zeros(1, 2*length(samples)));
data(1:2:(end-1)) = int8(markers);
data(2:2:end) = samples;
data = typecast(data, 'int16');

%markers2 = typecast(data, 'int8');
%markers2 = markers2(1:2:(end-1));
%figure(10); plot(markers2);

%% Write it to file
%fprintf('WARNING: If you name an existing file, it will be overwritten!')
[fileID,errmsg] = fopen(sprintf("%s.bin", filename), 'w', 'ieee-le');
if fileID < 0 
   error(errmsg);
end
fwrite(fileID,data,format);
fclose(fileID);

end
