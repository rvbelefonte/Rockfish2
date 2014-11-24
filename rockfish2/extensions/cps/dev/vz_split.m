function [vel_top,vel_bot,dz] = vz_split (vel_top,vel_bot,dz,Znew);

Znew = sort(Znew);
nZnew = length(Znew);

% generate layer boundaries at new depths
% zz(2) is depth to top of second layer, etc
% if VSP station is between ndx_lo and ndx_hi => station is in ndx_lo layer
for n = 1:nZnew
    zz = [0;cumsum(dz)];
    ndx_lo =  max(find(Znew(n) >= zz));
    ndx_hi = min(find(Znew(n) < zz));
    if (ndx_hi-ndx_lo > 1)
        error ('    Error in splitting velocity-depth data at additional depths!');
    end
    grad =  (vel_bot(ndx_lo)-vel_top(ndx_lo))/dz(ndx_lo);
    delta_z = Znew(n) -  zz(ndx_lo);
    tmp1 =  vel_top(ndx_lo) + grad*delta_z;
    vel_top = [vel_top(1:ndx_lo);tmp1;vel_top(ndx_lo+1:end)];
    vel_bot = [vel_bot(1:ndx_lo-1);tmp1;vel_bot(ndx_lo:end)];
    dz = [dz(1:ndx_lo-1);delta_z;dz(ndx_lo)-delta_z;dz(ndx_lo+1:end)];
end

return