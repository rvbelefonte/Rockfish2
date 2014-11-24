function [v,z] = vz_util3n(vtop,vbot,dz,dzmin);
%
% VZ_UTIL3 is a MATLAB function to reformat a velocity-depth
% function.   The input v(z) function is assumed to be specified 
% by the velocities at the top and bottom of each layer and the 
% layer thickness. The output function is specified by velocity 
% as a function of depth.  All first-order discontinuities are 
% replaced by thin layers of thickness "dzmin".
% NOTE:  Velocity is a continuous function of depth.
%
% USAGE: [v,z] = vz_util3(vtop,vbot,dz,dzmin);
%
%
% -------------------------------------- j.a.collins

if (nargin < 4)
   dzmin = 0.01;
end
delta_z = dzmin/2;

% Remove all velocity discontinuities by replacing zero-thickness layers with 
% layers of finite (but very small) thickness 
nlay = length(dz);
grad = (vbot-vtop)./dz;

clear vtopn vbotn dzn
vtopn(1) = vtop(1);
m = 1;
for n = 1:nlay-1
   if (vtop(n+1) ~= vbot(n))       % need to add a layer;
      dzn(m) = dz(n) - delta_z;    % change dz of finite-thickness layer
      dzn(m+1) = 2*delta_z;        % make zero thickness layer non-zero
      vbotn(m) = vbot(n) - grad(n)*delta_z;   % adjust velocity 
      vtopn(m+1) = vbotn(m);
      vbotn(m+1) = vtop(n+1) + grad(n+1)*delta_z;
      dz(n+1) = dz(n+1) - delta_z;
      m = m + 2;
   else
      vtopn(m) = vtop(n);
      vbotn(m) = vbot(n);
      dzn(m) = dz(n);
%%      vtopn(m+1) = vbot(m);
      m = m + 1;
   end
   vtopn(m) = vbotn(m-1);
end
vbotn(end+1) = vbot(nlay);
dzn(end+1) = dz(nlay);
vtopn = vtopn(:); vbotn = vbotn(:); dzn = dzn(:);

v = [vtopn; vbotn(end)];
z = cumsum(dzn); z = z(:); z = [0;z];

return;
