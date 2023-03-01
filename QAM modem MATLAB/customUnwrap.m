function out = customUnwrap(in, tol)
    for idx = 2:numel(in)
        delta = in(idx) - in(idx-1);
        if abs(delta) > abs(tol)
            in(idx:end) = in(idx:end) - delta;
        end
    end
    out = in;
end