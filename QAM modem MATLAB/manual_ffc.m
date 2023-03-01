function out = manual_ffc(in, order, topn, M, block)
    offset_angle = 45;
    shift_angle = 45;
    if M == 2
        offset_angle = 0;
        shift_angle = 90;

    end
    ideal = exp(1j*deg2rad(offset_angle));

    phase_error = zeros(1, floor(numel(in)/block));
    for loop_idx = 1:floor(numel(in)/block)
        idx_range = (1:block) + (loop_idx-1)*block;
        idx_range = idx_range(:);
        signal = in(idx_range);

        siga = signal;
        sigb = signal*exp(1j*deg2rad(shift_angle));
        
        if M == 2
            filta = (real(siga) >= 0);
            filtb = (real(sigb) >= 0);
        else
            filta = (real(siga) >= 0) & (imag(siga) >= 0);
            filtb = (real(sigb) >= 0) & (imag(sigb) >= 0);
        end
        
        siga = siga(filta);
        sigb = sigb(filtb);

        [~, idxa] = sort(abs(siga));
        [~, idxb] = sort(abs(sigb));

        % Sorted highest power to lowest.
        sorta = flipud(siga(idxa));
        sortb = flipud(sigb(idxb));

        topn = min([topn, numel(sorta), numel(sortb)]);
        thetaa = rad2deg(mean(angle(sorta(1:topn))));
        thetab = rad2deg(mean(angle(sortb(1:topn))));


        %{
        phia = (abs(siga).^pow).*angle(siga);
        phib = (abs(sigb).^pow).*angle(sigb);
        
        thetaa = rad2deg(mean(phia)/mean(abs(siga).^pow));
        thetab = rad2deg(mean(phib)/mean(abs(sigb).^pow));
        %}

        %[ma, idxa] = max(abs(siga));
        %[mb, idxb] = max(abs(sigb));

        %thetaa = rad2deg(angle(siga(idxa)));
        %thetab = rad2deg(angle(sigb(idxb)));


        % The difference between the two should be pi/4.  If it deviates from this
        % by very much, it means one of the two shifts puts the bulk of the symbols
        % on a decision boundary.
        err = 0;
        if abs(shift_angle - abs(thetaa - thetab)) > 5

            % THIS LOGIC IS THE PROBLEM
            if thetaa - thetab < 10
                % Choose the one with the lower error power
                errpowa = sum(abs(ideal - siga));
                errpowb = sum(abs(ideal - sigb));
                [~, idx] = min([errpowa, errpowb]);
            else
                % Choose the one closer to the ideal location
                [~, idx] = min(abs([thetaa, thetab] - offset_angle));
            end


            if idx == 1 % thetaa is the true angle
                err = offset_angle - thetaa;
            else % thetab is the true angle
                err = offset_angle - thetab - shift_angle; % thetab is already shifted
            end
        else
            err = offset_angle - thetaa;
        end
        
        phase_error(loop_idx) = err;
    end

    % BAD BAD I DON"T LIKE IT.  FIX ME!
    %phase_error = rad2deg(unwrap(deg2rad(phase_error)*50))/50;
    phase_error = customUnwrap(phase_error, 90);
    
    n = linspace(-1, 1, numel(phase_error));

    % Remove nan (caused by no symbols in decision region)
    filt = isnan(phase_error);
    phase_error(filt) = [];
    n(filt) = [];

    p = polyfit(n, phase_error, order);
    if p(1) > 10
        trash = 1;
    end
    x = linspace(-1, 1, numel(in));
    phase = polyval(p, x);
    phase = phase(:);
    out = in.*exp(1j*deg2rad(phase));
end