function [scaled] = AWG_write_CSV(samples, markers, notes, filename, sample_rate, autoscale)
%% Documentation
% This function - predictably - writes waveform data into a CSV format
% that can be read by the M8195A Arbitrary Waveform Generator.

% Samples should be a strictly real signal.

%% Scaling and digitization
% Scaling can be done internally on the AWG, but it's good form to do it
% here.
if autoscale
    % Set to zero mean.
    samples = samples - mean(samples);
    % Scale for maximum dynamic range
    samples = samples*(1/max(abs(samples)));
    scaled = samples;
end


%% Markers
% If ya want markers, now's the time to stick 'em in.
% Markers must be 2 bits or less - decimal three or below.
if (max(markers) > 3) || (min(markers) < 0)
    error("Marker resolution is only two bits - markers must be between 0 and 3.")
end

%% Inserting notes
% Currently, I don't know of a way to insert notes into this file type, so
% they're just discarded.


%% Combine samples and markers into single array
data = [samples(:), mod(markers, 2)==1, (markers(:) >= 2)]';


%% Write it to a CSV
[fid, msg] = fopen(sprintf("%s.csv", filename), 'wt');
if fid < 0
  error('Could not open file "%s" because "%s"', fid, msg);
end

fprintf(fid, 'SampleRate = %f GHz\n', sample_rate/1e9);
fprintf(fid, 'Y1, SampleMarker1, SampleMarker2\n');
filecontents = data(:)';
filecontents = filecontents(:);
fprintf(fid, '%f, %i, %i\n', filecontents);
fclose(fid);
end
