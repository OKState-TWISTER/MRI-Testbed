%inverse single scan fourier transform
%1-13-03

%YOU MUST HAVE BOTH FFT AND ITS MIRROR IMAGE FOR THIS TO WORK RIGHT!!!
%USE singfourSAFE to ensure things are proper

function [t,out]= invsingfourSAFE(f,fdata)
Npts=length(fdata);  				        
out=real(ifft(fdata,'symmetric'));    
%out=(ifft(fdata,'symmetric'));  
deltaf=f(2)-f(1); 
t=1/deltaf*(0:(Npts-1))/Npts;
