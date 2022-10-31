function [S11,S21] = MakeStackAngle2(f, stack, theta_incident, polarization)
% This function calculates S-matrix components for an arbitrary stratified
% dielectric stack at off-normal incidence.  This function is based on the
% work of Born and Wolf.  See "Principles of Optics, 7th edition," pages
% 58-70.
% Currently, this code assumes the wave is transverse electric (TE) unless specified otherwise.
% Incidence angle is referenced to normal incidence.  That is, 0 radians is
% normal incidence, +/- pi/2 is perfectly oblique.
% The stack is given in thickness index pairs, like so:
% stack = [thicknesses(:), indicies(:)];

% Sanitize polarization input
if((polarization ~= 'S')&&(polarization ~= 'P'))
    fprintf("WARNING: In makestackangle2: Specify polarization as P or S. P-polarization assumed.");
    polarization = 'P';
end

c = 299792458;
j = -sqrt(-1);
lambda = c./f;

% Set up vectors (prop. angle and constant 'p' or 'q') for each layer.
theta = zeros(1,length(stack));
theta(1) = theta_incident;
for kk = 1:length(theta)-1
    % Snell's law.
    theta(kk+1) = asin((stack(kk,2)/stack(kk+1,2))*sin(theta(kk)));
end
    if(polarization == 'S')
        p = (stack(:,2)').*cos(theta); % TE incidence (S-polarization)
    else
        p = (1./stack(:,2)').*cos(theta); % TM incidence (P-polarization)
    end
% M is the characteristic matrix of the stratified medium, and it is found
% by multiplying the characteristic matricies of the constituent dielectric
% layers.
M = repmat(eye(2,2), [1 1 length(f)]);
% Iterate over the dielectric layers, assembling the composite
% characteristic matrix as we go.
for kk = 2:length(stack)-1
    B = (2*pi./lambda)*stack(kk,2)*stack(kk,1)*cos(theta(kk));
        m11 = cos(B);
        m12 = -(j/p(kk))*sin(B);
        m21 = -j*p(kk)*sin(B);
        m22 = m11;
    Mkk = [shiftdim(m11,-1) shiftdim(m12,-1); shiftdim(m21,-1) shiftdim(m22,-1)];

    for qq = 1:length(f)
        M(:,:,qq) = M(:,:,qq)*Mkk(:,:,qq);
    end
end

m11 = shiftdim(M(1,1,:),1);
m12 = shiftdim(M(1,2,:),1);
m21 = shiftdim(M(2,1,:),1);
m22 = shiftdim(M(2,2,:),1);

pL = p(end);
S11 = ((m11+m12*pL)*p(1) - (m21+m22*pL))./((m11+m12*pL)*p(1) + (m21+m22*pL));  % reflection coefficient
S21 = (2*p(1))./((m11+m12*pL)*p(1) + (m21+m22*pL)); % transmission coefficient
end