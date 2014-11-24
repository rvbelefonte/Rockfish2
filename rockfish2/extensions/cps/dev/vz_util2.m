function [v,z] = vz_util2(vtop,vbot,dz);
%
% VZ_UTIL2 is a MATLAB function to reformat a velocity-depth
% function.   The input v(z) function is assumed to be specified 
% by the velocities at the top and bottom of each layer and the 
% layer thickness. The output function is specified by velocity 
% as a function of depth.
%
% USAGE: [v,z] = vz_util2(vtop,vbot,dz);
%
% -------------------------------------- j.a.collins

mlay = length(vtop);
z = zeros(2*mlay,1);
v = zeros(2*mlay,1);
z(1) = 0.0;
for (m = 1:mlay)
  n = 2*m - 1;
  v(n) = vtop(m);
  v(n+1) = vbot(m);
  if (n > 1)
    z(n) = z(n-1);
  end
  z(n+1) = z(n) + dz(m);
end
