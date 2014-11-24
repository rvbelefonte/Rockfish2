function [vtop,vbot,dz] = vz_util1(v,z);
%
% VZ_UTIL1 is a MATLAB function to reformat a velocity-depth
% function.   The input v(z) function is assumed to be specified 
% by velocity as a function of depth.  The output function is 
% expressed by explicitly specifying the velocities at the
% top and bottom of each layer and the layer thickness. 
%
% USAGE: [vtop,vbot,dz] = vz_util1(v,z);

mpts = length(v);
vtop = v(1:mpts-1);
vbot = v(2:mpts);
dz = diff(z);

ndx = (dz == 0);
vtop(find(ndx)) = [];
vbot(find(ndx)) = [];
dz(find(ndx)) = [];
