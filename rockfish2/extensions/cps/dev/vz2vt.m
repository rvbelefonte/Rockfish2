function [dT] = vz2vt(vtop,vbot,dz);
%
% Function VZ2VT transforms velocity as a function of depth 
% to velocity as a function of one-way travel time.
%
% USAGE: [dT] = vz2vt(vtop,vbot,dz);

% -------------------------------------------------------- jac 

nlay = length(vtop);
if (nlay ~= length(vbot) | nlay ~= length(dz))
  error ('Inconsistent dimensions for V(z) input function');
end

grad = (vbot-vtop)./dz;
ndx = abs(grad) > eps;
dT = zeros(nlay,1);
dT(ndx) = ( log(vbot(ndx)) - log(vtop(ndx)) )./grad(ndx);
dT(~ndx) = dz(~ndx)./vtop(~ndx);

return
