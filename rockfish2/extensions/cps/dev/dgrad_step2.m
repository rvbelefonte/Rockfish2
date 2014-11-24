function [vel,dzn] = dgrad_step2(vtop,vbot,dz,dz_new,n_iso);
%
% MATLAB function "dgrad_step2" transforms a velocity-depth function 
% parameterized by iso-velocity and linear gradient layers to a 
% velocity-depth function parameterized by iso-velocity layers only.
%
%												j.a.collins
%
% USAGE: [vel,dzn] = dgrad_step2(vtop,vbot,dz,dz_new,n_iso);


nlayrs = length(dz);
nn = 1;
for n = 1:nlayrs
    if (n_iso(n) == 1)
        vel(nn) = (vtop(n) + vbot(n))/2;
        dzn(nn) = dz_new(n);
        nn = nn + 1;
    else
        mlay = n_iso(n);
        v_inc = (vbot(n)-vtop(n))/mlay;
        mlay = mlay + 1;   
        for (m = 1:mlay)  
            vel(nn) =  vtop(n) + (m-1)*v_inc; 
            if (m == 1 | m == mlay)
                dzn(nn) = dz_new(n)/2;
            else
                dzn(nn) = dz_new(n);
            end
            nn = nn + 1;
        end
    end
end

