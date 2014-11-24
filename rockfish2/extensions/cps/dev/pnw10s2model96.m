function [Vel_p,Vel_s,Z] = pnw10s2model96(Hw);
%
% The Matlabfunction "pnw10s2model96.m" generates and writes an earth-model file for input to 
% Bob Herrmann's programs "sprep96" and "sdisp96". The output file is in "model96" format.
% The function takes one argument, "Hw", the water depth in kilometers

fmax = 0.5;
lambda_fracn = 1;


cd /Users/jac/Projects/SeaJade/Calibration/Earth_Model
disp(' ');
%vz_infile = input ('    Name of file with Porritt-Allen-Boyarko_Brudzinski velocity model PNW10-S?  ', 's');
vz_infile = 'Porritt_Allen_Cascadia_Vs.txt';
Data_Path = '/Users/jac/Projects/SeaJade/Calibration/Earth_Model';   
filein = strcat(Data_Path,'/',vz_infile);

%[radius, lat, lon, dvs, Vs] = textread(filein, '%f %f %f %f %f\n','headerlines',1);
[radius, lat, lon, dvs, Vs] = textread(filein, '%f %f %f %f %f\n');

Z = abs(radius - radius(1));
Z = Z(:); Vs = Vs(:);
Vp = 0.9409 + 2.0947*Vs - 0.8206*Vs.^2 + 0.2683*Vs.^3 - 0.0251*Vs.^4; % Brocher, BSSA, 2005

% copy Vp and Vs
Vel_p = Vp; Vel_s = Vs;

% Vs
[vtop,vbot,dz] = vz_util1(Vs,Z);
[dz_new,n_iso] = dgrad_step1(vtop,vbot,dz,fmax,lambda_fracn);
[vel,dzn] = dgrad_step2(vtop,vbot,dz,dz_new,n_iso);
Vs = vel(:); 
dZ = dzn(:);

% Vp; use same "n_iso" and "dz" as for Vs
[vtop,vbot,dz] = vz_util1(Vp,Z);
[vel,dzn] = dgrad_step2(vtop,vbot,dz,dz_new,n_iso);
if (dzn(:) ~= dZ)
   error ('    error making iso-velocity layers!')
end
Vp = vel(:);

rho = 1.6612*Vp - 0.4721*Vp.^2 + 0.0671*Vp.^3 - 0.0043*Vp.^4 + 0.000106*Vp.^5; % Brocher, BSSA, 2005

% Qs 
Qs = zeros(size(dZ));
ndx = min(find(Vp > 7.5));
Qs(ndx:end) = 150;
Qs(1:ndx-1) = 10000;

% Qp
Qp = zeros(size(dZ));
Qp(ndx:end) = 2*Qs(ndx:end);
Qp(1:ndx-1) = 2*Qs(1:ndx-1);

% Misc
etap = zeros(size(dZ));
etas = zeros(size(dZ));
frefp=ones(size(dZ));
frefs=ones(size(dZ));

% add water layer
Vs = [0; Vs];
Vp = [1.50; Vp];
rho = [1.020; rho];
dZ = [Hw; dZ];
Qp = [99999; Qp];
Qs = [99999; Qs];
etap = [0.0; etap];
etas = [0.0; etas];
frefp = [1.0; frefp];
frefs = [1.0; frefs];


%%%%%%%%%
Data_Path = '/Users/jac/Projects/SeaJade/Calibration/Earth_Model';   
fileout = strcat(Data_Path,'/','pnw10s_model96.txt');
fop = fopen (fileout,'w');
fprintf(fop,'MODEL.01 \n');
fprintf(fop,'Porritt-Allen-Boyarko_Brudzinski Velocity Model PNW10-S \n');
fprintf(fop,'ISOTROPIC \n');
fprintf(fop,'KGS \n');
fprintf(fop,'FLAT EARTH \n');
fprintf(fop,'1-D \n');
fprintf(fop,'CONSTANT VELOCITY \n');
fprintf(fop,'LINE08 \n');
fprintf(fop,'LINE09 \n');
fprintf(fop,'LINE10 \n');
fprintf(fop,'LINE11 \n');
fprintf(fop,'  H      VP      VS     RHO    QP        QS       ETAP   ETAS  FREFP FREFS \n');

for n = 1:length(dZ)
   fprintf ( fop, '%5.2f   %5.2f   %5.2f  %5.2f   %7.1f   %7.1f  %4.1f   %4.1f  %4.1f  %4.1f\n', ...
           dZ(n), Vp(n), Vs(n), rho(n), Qp(n),   Qs(n), etap(n), etas(n), frefp(n), frefs(n) );
end


%%%%%%%%%%%%%%%
% At the command line:
% sprep96 -M pnw10s_model96.txt -d pnw10s_dfile.txt -HS 1.0 -HR 1.0 -DT 1 -NPTS 4096 -NMOD 1 -R
% sdisp96
% sdpsrf96 -R -TXT
% cp -p SDISPR.TXT pnw10s_phase_velocity.txt
% 
