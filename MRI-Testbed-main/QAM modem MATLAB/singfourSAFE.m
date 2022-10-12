%single scan fourier transform
%SAFE because it will not throw away mirror image data and doesn't use zero padding
%1-10-01
%9-7-01 added option of specifying color of plot 
%usage:  singfour(x,y,C) where C is a color as specified in 
%PLOT command such as 'c' for cyan, 'g' for green, etc.
%x should be expressed in seconds


function [f,dummy]= singfourSAFE(x,y,varargin)

  
dummy=fft(y);		                    %for amplitude spectrum (fft.m automatically does zero padding by telling number
numpts=length(y);						%adjust x-axis (freq) scale for spectrum plot
deltat=x(2)-x(1);                       %find time step
deltaf=1/deltat;                        %find bandwidth of step
f=deltaf*(0:(numpts-1))/numpts+eps;     %split bandwidth into vector of frequencies (add eps to offset zero slightly)
plotyes=0;

if plotyes==1
	figure(1);
	hold on;
	if nargin==3
        plot(f,abs(dummy),varargin{1}); 
	else
        plot(f,abs(dummy));
	end
	grid on;
	xlabel('Hz'); ylabel('Amplitude');
end
