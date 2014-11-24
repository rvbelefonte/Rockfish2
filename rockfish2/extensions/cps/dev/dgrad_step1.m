function [dz_new,n_iso] = dgrad_step1(vtop,vbot,dz,fmax,lambda_fracn);
%
% MATLAB function "dgrad_step1" determines the thicknesses of the stack of
% iso-velocity layers required to approximate a velocity-depth function
% parameterized by a stack of linear gradient layers.  Variable "fmax" is 
% max. frequency of interest.  Variable "lambda_fracn" is max. thickness
% of iso-velocity layers as a fraction of a wavelength.
%
%                                           --j.a.collins
%
% USAGE: [dz_new,n_iso] = dgrad_step1(vtop,vbot,dz,fmax,lambda_fracn);


dv_min = 1e-3;  % km/s;
dv = vbot - vtop;

nlayrs = length(dz);
for n = 1:nlayrs;
    if (abs(dv(n)) < dv_min)
        dz_new(n) = dz(n);
        n_iso(n) = 1;
    else
        vmin = min(vtop(n),vbot(n));
        lambda_min = vmin/fmax;
        zinc = lambda_min*lambda_fracn;
        mlay = floor(dz(n)/zinc);
        if (zinc*mlay < dz(n)) 
            mlay = mlay + 1;
            zinc = dz(n)/mlay;
        end
        dz_new(n) = zinc;
        n_iso(n) = mlay;
    end
end
