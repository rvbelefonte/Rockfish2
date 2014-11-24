%disp(' ');
%fname = input ('    Name of file with seismic data?  ', 's');
fname = 'seis_herr_disp.txt';
fid = fopen(fname,'r');
if (fid == -1)
    error (['    Cannot open file: ', fname]);
end

% skip forward and determine # of data points per trace
for n = 1:18
    [jnk] = fgetl(fid);
end
str = fgetl(fid);  [cmpa,cmpinc,dt,npts] = strread(str,'%f %f %f %d',1);

% Now back up and read relevant parts of data header
frewind(fid)

%%% read select lines from header
for n = 1:3
    [jnk] = fgetl(fid);
end
str = fgetl(fid);  [units] = strread(str,'%s',1);
str = fgetl(fid);  % skip line
str = fgetl(fid);  [jnk,jnk,jnk,jnk,jnk,jnk,jnk,jnk,event_depth] = strread(str,'%s %s %s %d %s %s %s %s %f',1);
str = fgetl(fid);  % skip line
str = fgetl(fid);  % skip line
str = fgetl(fid);  [dist_km, jnk, event_station_azim] = strread(str,'%f %f %f',1);
for n = 1:3
    [jnk] = fgetl(fid);
end
str = fgetl(fid);  [P_time, SV_time, SH_time] = strread(str,'%f %f %f',1);
str = fgetl(fid);  [A,C,F,L,N,Rho] = strread(str,'%f %f %f %f %f %f',1);

for n = 1:3
    [jnk] = fgetl(fid);
end

clear seis component;
ncmpts = 3;
seis = zeros(npts,ncmpts);
for n = 1:ncmpts
    str = fgetl(fid);  [component(n)] = strread(str,'%s',1);
%-- cmpaz:  Positive motion in this azimuthal direction: 0 = north, 90 = east (SEED)
%-- cmpinc  Positive motion in this direction with vertical: -90 = up, 0 = horiz, 90 = down (SEED)
    str = fgetl(fid);  [cmpa,cmpinc,dt,npts] = strread(str,'%f %f %f %d',1);
    str = fgetl(fid);  [yr_start,month_start,day_start,hour_start,min_start,secnd_start] = strread(str,'%d %d %d %d %d %f',1);
    time_offset = secnd_start;

    seis(:,n) = fscanf (fid,'%f',[npts,1]);
    str = fgetl(fid);   % move on past eol.
end    

figure
tlo = 0; thi = 40;
subplot(311)
pltseis(seis(:,1),dt,time_offset,tlo,thi);
title (['Component: ' char(component(1))]);
xlabel ('Time (s)')
ylabel (['Amplitude (' lower(char(units)),')'])
subplot(312);
pltseis(seis(:,2),dt,time_offset,tlo,thi);
title (['Component: ' char(component(2))]);
xlabel ('Time (s)')
ylabel (['Amplitude (' lower(char(units)),')'])
subplot(313);
pltseis(seis(:,3),dt,time_offset,tlo,thi);
title (['Component: ' char(component(3))]);
xlabel ('Time (s)')
ylabel (['Amplitude (' lower(char(units)),')'])
