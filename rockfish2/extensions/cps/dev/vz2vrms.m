function [vrms,z,tt] = vz2vrms(vtop,vbot,dz);
%
% MATLAB function "vz2vrms" transforms velocity as a function of depth 
% to root-mean-square velocity as a function of depth. 
%
% USAGE: [vrms,z,tt] = vz2vrms(vtop,vbot,dz);

% -------------------------------------------------------- jac 

nlay = length(vtop);
if (nlay ~= length(vbot) | nlay ~= length(dz))
  error ('Inconsistent dimensions for V(z) input function');
end

grad = (vbot-vtop)./dz;
dT = zeros(nlay,1);
ndx = find((abs(grad > eps)));
if (~isempty(ndx))
    dT(ndx) = ( log(vbot(ndx)) - log(vtop(ndx)) )./grad(ndx);
    dT(~ndx) = dz(~ndx)./vtop(~ndx);
else
    dT = dz./vtop;
end
vel_int = dz./dT;   % "average" interval velocity
vel_int2 = vel_int.^2;


dT2 = 2*dT;
tmp = cumsum(vel_int2.*dT2);
tt = cumsum(dT2); tt = tt(:);

vrms = sqrt(tmp./tt);

z = cumsum(dz); z = z(:);
return

