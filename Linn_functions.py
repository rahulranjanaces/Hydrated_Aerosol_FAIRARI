# AO18_Linn_functions.py but added some functions
import sys  
sys.path.insert(0, 'C:/Users/AlmuthNeuberger/Documents/PythonScripts/Italy-campaign22')
import Data_excluded
import numpy as np
import pandas as pd
import glob2
import glob, os
from io import BytesIO
import datetime as dt
import calendar
from pandas.errors import EmptyDataError
from scipy.ndimage.interpolation import shift


# Function for selecting files between starttime and endtime
def timeselect(f,date,datefmt,starttime,endtime,timefmt):            
    start = calendar.timegm(dt.datetime.strptime(starttime, timefmt).date().timetuple())
    end = calendar.timegm(dt.datetime.strptime(endtime, timefmt).date().timetuple())
    #if (not os.path.isfile(f)):
    #    return 0
    ctime=calendar.timegm(dt.datetime.strptime(date, datefmt).date().timetuple())
    #(mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(f)

    return start<=ctime and end>=ctime



# Function for excluding data that should not be used (inbetween starttime and endtime)
def excludeData(data=None,starttime_exclude=None,endtime_exclude=None):
    for start in range(len(starttime_exclude)):
        data = data.loc[(data.index<starttime_exclude[start])|(data.index>endtime_exclude[start])]
    return data

# Function for keeping data that should be used (inbetween starttime and endtime, fog events)
def keepData(data=None,starttime_exclude=None,endtime_exclude=None):
    for start in starttime_exclude.index:
        data_n = data.loc[(starttime_exclude[start]<=data.index)&(data.index<=endtime_exclude[start])]
        if start==starttime_exclude.index[0]:
            data_f=data_n
        else:
            data_f=pd.concat([data_f,data_n],axis=0) #data_f.append(data_n)
    return data_f

# Function to calculate fog times and save them as an excel file
def fog_times_old(CVI_ignore=120, scantime=None, scantime_at_end=None, CVI_scannumber=3, DMPS=None, GCVI=None,save_to=None):
    if (scantime==None)|(scantime_at_end==None)|(DMPS.empty)|(GCVI.empty)|(save_to==None):
        print('no scantime for DMPS or no data for DMPS or no data for GCVI given \nor not defined if scantime is time at the end of the scan or not \nor no file for saving defined')
    else:
        ## set DMPS scan time to the end of the scan (Rackham: adding 6min as scan takes 12min, Madam: adding 4:30min as scan takes 9min)
        DMPSend=DMPS.copy()
        if (scantime_at_end=='No')|(scantime_at_end=='no'):
            DMPSend.index=DMPS.index+pd.Timedelta('%fS'%float(scantime/2))
        
        GCVI=GCVI.asfreq(freq='1S', method='ffill') ## sometimes a second is missing, fill it with the last value
        GCVI=GCVI.assign(count=GCVI.groupby(GCVI.sum_stat.ne(GCVI.sum_stat.shift()).cumsum()).cumcount().add(1))
        GCVI=GCVI.iloc[np.where((GCVI['windtunl']=='Automatc') & (GCVI['sum_stat']==4))]
        
        DMPSend_C=pd.concat([GCVI,DMPSend.resample('1S').mean()],axis=1)
        DMPSend_C=DMPSend_C.iloc[np.where((DMPSend_C['windtunl']=='Automatc') & (DMPSend_C['sum_stat']==4) & (DMPSend_C['count']>(CVI_ignore+scantime)))]  ## select only time when CVI was on
        DMPSend_C=DMPSend_C.dropna(axis=1,how='all')
        DMPSend_C=DMPSend_C.dropna(subset=['1.500E-8','7.920E-7'],how='all')
        DMPSend_C['event'] = ((DMPSend_C['windtunl']=='Automatc')&(DMPSend_C['sum_stat']==4)&(DMPSend_C['count']>(CVI_ignore+scantime))&((DMPSend_C['count'].diff() < 0.9*scantime)|(DMPSend_C['count'].diff() > 1.1*scantime))).cumsum() #for FAIRARI: scantime-2 and scantime+2 
        DMPSend_C=DMPSend_C.join(DMPSend_C.groupby('event').count(), on='event',rsuffix='_r')
        DMPSend_C=DMPSend_C.iloc[:,:50]
        DMPSend_C=DMPSend_C.rename(columns={'visiblty':'event_scan'})
        DMPSend_C.drop(DMPSend_C[DMPSend_C['event_scan'] < CVI_scannumber].index, inplace=True)
        DMPSend_C['event_incl'] = ((DMPSend_C['windtunl']=='Automatc')&(DMPSend_C['sum_stat']==4)&(DMPSend_C['count']>(CVI_ignore+scantime))&((DMPSend_C['count'].diff() < 0.9*scantime)|(DMPSend_C['count'].diff() > 1.1*scantime))).cumsum() #for FAIRARI: scantime-2 and scantime+2 
        
        starttime_fog= []
        endtime_fog= []
        for key in DMPSend_C.groupby(['event_incl']).mean().index:
            fog_start = dt.datetime.strptime(str(DMPSend_C.groupby('event_incl').get_group(key).index[0]), '%Y-%m-%d %H:%M:%S')-pd.Timedelta('%iS'%scantime)
            starttime_fog.append(fog_start)
            fog_end = dt.datetime.strptime(str(DMPSend_C.groupby('event_incl').get_group(key).index[-1]), '%Y-%m-%d %H:%M:%S')
            endtime_fog.append(fog_end)
        df = pd.DataFrame([DMPSend_C.groupby('event_incl').mean().index,starttime_fog,endtime_fog]).transpose()
        df.to_excel('%s.xlsx'%save_to, header=['fog_nr','starttime_fog','endtime_fog'], index=None)
        print(df)

# Function to calculate fog times and save them as an excel file
def fog_times(CVI_ignore=120, scantime=None, scantime_at_end=None, CVI_scannumber=3, DMPS=None, GCVI=None,save_to=None):
    if (scantime==None)|(scantime_at_end==None)|(DMPS.empty)|(GCVI.empty)|(save_to==None):
        print('no scantime for DMPS or no data for DMPS or no data for GCVI given \nor not defined if scantime is time at the end of the scan or not \nor no file for saving defined')
    else:
        ## set DMPS scan time to the end of the scan (Rackham: adding 6min as scan takes 12min, Madam: adding 4:30min as scan takes 9min)
        DMPSend=DMPS.copy()
        if (scantime_at_end=='No')|(scantime_at_end=='no'):
            DMPSend.index=DMPS.index+pd.Timedelta('%fS'%float(scantime/2))
        
        GCVI=GCVI.asfreq(freq='1S', method='ffill') ## sometimes a second is missing, fill it with the last value
        GCVI=GCVI.assign(count=GCVI.groupby(GCVI.sum_stat.ne(GCVI.sum_stat.shift()).cumsum()).cumcount().add(1))
        GCVI=GCVI.iloc[np.where((GCVI['windtunl']=='Automatc') & (GCVI['sum_stat']==4))]
        
        DMPSend_C=pd.concat([GCVI,DMPSend.resample('1S').mean()],axis=1)
        DMPSend_C=DMPSend_C.iloc[np.where((DMPSend_C['windtunl']=='Automatc') & (DMPSend_C['sum_stat']==4) & (DMPSend_C['count']>(CVI_ignore+scantime)))]  ## select only time when CVI was on
        DMPSend_C=DMPSend_C.dropna(axis=1,how='all')
        DMPSend_C=DMPSend_C.dropna(subset=['1.500E-8','7.920E-7'],how='all')
        DMPSend_C['event'] = ((DMPSend_C['windtunl']=='Automatc')&(DMPSend_C['sum_stat']==4)&(DMPSend_C['count']>(CVI_ignore+scantime))&((DMPSend_C['count'].diff() < 0.9*scantime)|(DMPSend_C['count'].diff() > 1.1*scantime))).cumsum()
        #DMPSend_C=DMPSend_C.join(DMPSend_C.groupby('event').count(), on='event',rsuffix='_r')
        DMPSend_C['event_scan'] = DMPSend_C['event'].groupby(DMPSend_C['event']).transform('count')
        #print(DMPSend_C)
        #DMPSend_C=DMPSend_C.iloc[:,:50]
        #DMPSend_C=DMPSend_C.rename(columns={'visiblty':'event_scan'})
        DMPSend_C.drop(DMPSend_C[DMPSend_C['event_scan'] < CVI_scannumber].index, inplace=True)
        DMPSend_C['event_incl'] = ((DMPSend_C['windtunl']=='Automatc')&(DMPSend_C['sum_stat']==4)&(DMPSend_C['count']>(CVI_ignore+scantime))&((DMPSend_C['count'].diff() < 0.9*scantime)|(DMPSend_C['count'].diff() > 1.1*scantime))).cumsum() #for FAIRARI: scantime-2 and scantime+2 
        
        starttime_fog= []
        endtime_fog= []
        for key in DMPSend_C.groupby(['event_incl']).mean().index:
            fog_start = dt.datetime.strptime(str(DMPSend_C.groupby('event_incl').get_group(key).index[0]), '%Y-%m-%d %H:%M:%S')-pd.Timedelta('%iS'%scantime)
            starttime_fog.append(fog_start)
            fog_end = dt.datetime.strptime(str(DMPSend_C.groupby('event_incl').get_group(key).index[-1]), '%Y-%m-%d %H:%M:%S')
            endtime_fog.append(fog_end)
        df = pd.DataFrame([DMPSend_C.groupby('event_incl').mean().index,starttime_fog,endtime_fog]).transpose()
        df.to_excel('%s.xlsx'%save_to, header=['fog_nr','starttime_fog','endtime_fog'], index=None)
        print(df)        

# Function to calculate fog times and save them as an excel file
def fog_times_Vis(CVI_ignore=120, CVI_scannumber=3*12*60, GCVI=None,save_to=None):
    if (GCVI.empty)|(save_to==None):
        print('no data for GCVI given \nor no file for saving defined')
    else:
        GCVI=GCVI.asfreq(freq='1S', method='ffill') ## sometimes a second is missing, fill it with the last value
        GCVI=GCVI.assign(count=GCVI.groupby(GCVI.sum_stat.ne(GCVI.sum_stat.shift()).cumsum()).cumcount().add(1))

        endtime_fog=GCVI[(GCVI['count'].diff().shift(periods=-1)<-(CVI_scannumber+CVI_ignore))&(GCVI['sum_stat']==4)].index
        starttime_fog=endtime_fog-pd.TimedeltaIndex(GCVI[(GCVI['count'].diff().shift(periods=-1)<-(CVI_scannumber+CVI_ignore))&(GCVI['sum_stat']==4)]['count'], unit='S')

        df = pd.DataFrame([range(0,np.size(starttime_fog.values)),starttime_fog,endtime_fog]).transpose()
        df.to_excel('%s.xlsx'%save_to, header=['fog_nr','starttime_fog','endtime_fog'], index=None)
        print(df)
        
        
# Function to calculate haze times and save them as an excel file
def haze_times(CVI_ignore=120, scantime=None, scantime_at_end=None, CVI_scannumber=3, DMPS=None, GCVI=None,save_to=None):
    if (scantime==None)|(scantime_at_end==None)|(DMPS.empty)|(GCVI.empty)|(save_to==None):
        print('no scantime for DMPS or no data for DMPS or no data for GCVI given \nor not defined if scantime is time at the end of the scan or not \nor no file for saving defined')
    else:
        ## set DMPS scan time to the end of the scan (Rackham: adding 6min as scan takes 12min, Madam: adding 4:30min as scan takes 9min)
        DMPSend=DMPS.copy()
        if (scantime_at_end=='No')|(scantime_at_end=='no'):
            DMPSend.index=DMPS.index+pd.Timedelta('%fS'%float(scantime/2))
        
        GCVI=GCVI.asfreq(freq='1S', method='ffill') ## sometimes a second is missing, fill it with the last value
        GCVI=GCVI.assign(count=GCVI.groupby(GCVI.sum_stat.ne(GCVI.sum_stat.shift()).cumsum()).cumcount().add(1))
        GCVI=GCVI.iloc[np.where((GCVI['windtunl']=='Automatc') & (GCVI['sum_stat']==0) & (GCVI['visiblty']<=5000)& (GCVI['visiblty']>2000))]
        
        DMPSend_C=pd.concat([GCVI,DMPSend.resample('1S').mean()],axis=1)
        DMPSend_C=DMPSend_C.iloc[np.where((DMPSend_C['windtunl']=='Automatc') & (DMPSend_C['sum_stat']==0) & (DMPSend_C['count']>(CVI_ignore+scantime)))]  ## select only time when CVI was off
        DMPSend_C=DMPSend_C.dropna(axis=1,how='all')
        DMPSend_C=DMPSend_C.dropna(subset=['1.500E-8','7.920E-7'],how='all')
        DMPSend_C['event'] = ((DMPSend_C['windtunl']=='Automatc')&(DMPSend_C['sum_stat']==0)&(DMPSend_C['count']>(CVI_ignore+scantime))&((DMPSend_C['count'].diff() < 0.9*scantime)|(DMPSend_C['count'].diff() > 1.1*scantime))).cumsum()
        DMPSend_C=DMPSend_C.join(DMPSend_C.groupby('event').count(), on='event',rsuffix='_r')
        DMPSend_C=DMPSend_C.iloc[:,:50]
        DMPSend_C=DMPSend_C.rename(columns={'visiblty':'event_scan'})
        DMPSend_C.drop(DMPSend_C[DMPSend_C['event_scan'] < CVI_scannumber].index, inplace=True)
        DMPSend_C['event_incl'] = ((DMPSend_C['windtunl']=='Automatc')&(DMPSend_C['sum_stat']==0)&(DMPSend_C['count']>(CVI_ignore+scantime))&((DMPSend_C['count'].diff() < 0.9*scantime)|(DMPSend_C['count'].diff() > 1.1*scantime))).cumsum()
        
        starttime_nofog= []
        endtime_nofog= []
        for key in DMPSend_C.groupby(['event_incl']).mean().index:
            nofog_start = dt.datetime.strptime(str(DMPSend_C.groupby('event_incl').get_group(key).index[0]), '%Y-%m-%d %H:%M:%S')-pd.Timedelta('%iS'%scantime)
            starttime_nofog.append(nofog_start)
            nofog_end = dt.datetime.strptime(str(DMPSend_C.groupby('event_incl').get_group(key).index[-1]), '%Y-%m-%d %H:%M:%S')
            endtime_nofog.append(nofog_end)
        df = pd.DataFrame([DMPSend_C.groupby('event_incl').mean().index,starttime_nofog,endtime_nofog]).transpose()
        df.to_excel('%s.xlsx'%save_to, header=['haze_nr','starttime_haze','endtime_haze'], index=None)
        print(df)

# Function to calculate mist times and save them as an excel file
def mist_times(CVI_ignore=120, scantime=None, scantime_at_end=None, CVI_scannumber=3, DMPS=None, GCVI=None,save_to=None):
    if (scantime==None)|(scantime_at_end==None)|(DMPS.empty)|(GCVI.empty)|(save_to==None):
        print('no scantime for DMPS or no data for DMPS or no data for GCVI given \nor not defined if scantime is time at the end of the scan or not \nor no file for saving defined')
    else:
        ## set DMPS scan time to the end of the scan (Rackham: adding 6min as scan takes 12min, Madam: adding 4:30min as scan takes 9min)
        DMPSend=DMPS.copy()
        if (scantime_at_end=='No')|(scantime_at_end=='no'):
            DMPSend.index=DMPS.index+pd.Timedelta('%fS'%float(scantime/2))
        
        GCVI=GCVI.asfreq(freq='1S', method='ffill') ## sometimes a second is missing, fill it with the last value
        GCVI=GCVI.assign(count=GCVI.groupby(GCVI.sum_stat.ne(GCVI.sum_stat.shift()).cumsum()).cumcount().add(1))
        GCVI=GCVI.iloc[np.where((GCVI['windtunl']=='Automatc') & (GCVI['sum_stat']==0) & (GCVI['visiblty']<=2000)& (GCVI['visiblty']>1000))]
        
        DMPSend_C=pd.concat([GCVI,DMPSend.resample('1S').mean()],axis=1)
        DMPSend_C=DMPSend_C.iloc[np.where((DMPSend_C['windtunl']=='Automatc') & (DMPSend_C['sum_stat']==0) & (DMPSend_C['count']>(CVI_ignore+scantime)))]  ## select only time when CVI was off
        DMPSend_C=DMPSend_C.dropna(axis=1,how='all')
        DMPSend_C=DMPSend_C.dropna(subset=['1.500E-8','7.920E-7'],how='all')
        DMPSend_C['event'] = ((DMPSend_C['windtunl']=='Automatc')&(DMPSend_C['sum_stat']==0)&(DMPSend_C['count']>(CVI_ignore+scantime))&((DMPSend_C['count'].diff() < 0.9*scantime)|(DMPSend_C['count'].diff() > 1.1*scantime))).cumsum()
        DMPSend_C=DMPSend_C.join(DMPSend_C.groupby('event').count(), on='event',rsuffix='_r')
        DMPSend_C=DMPSend_C.iloc[:,:50]
        DMPSend_C=DMPSend_C.rename(columns={'visiblty':'event_scan'})
        DMPSend_C.drop(DMPSend_C[DMPSend_C['event_scan'] < CVI_scannumber].index, inplace=True)
        DMPSend_C['event_incl'] = ((DMPSend_C['windtunl']=='Automatc')&(DMPSend_C['sum_stat']==0)&(DMPSend_C['count']>(CVI_ignore+scantime))&((DMPSend_C['count'].diff() < 0.9*scantime)|(DMPSend_C['count'].diff() > 1.1*scantime))).cumsum()
        
        starttime_nofog= []
        endtime_nofog= []
        for key in DMPSend_C.groupby(['event_incl']).mean().index:
            nofog_start = dt.datetime.strptime(str(DMPSend_C.groupby('event_incl').get_group(key).index[0]), '%Y-%m-%d %H:%M:%S')-pd.Timedelta('%iS'%scantime)
            starttime_nofog.append(nofog_start)
            nofog_end = dt.datetime.strptime(str(DMPSend_C.groupby('event_incl').get_group(key).index[-1]), '%Y-%m-%d %H:%M:%S')
            endtime_nofog.append(nofog_end)
        df = pd.DataFrame([DMPSend_C.groupby('event_incl').mean().index,starttime_nofog,endtime_nofog]).transpose()
        df.to_excel('%s.xlsx'%save_to, header=['mist_nr','starttime_mist','endtime_mist'], index=None)
        print(df)


# Function to calculate non-fog times and save them as an excel file
def nofog_times(CVI_ignore=120, scantime=None, scantime_at_end=None, CVI_scannumber=3, DMPS=None, GCVI=None,save_to=None):
    if (scantime==None)|(scantime_at_end==None)|(DMPS.empty)|(GCVI.empty)|(save_to==None):
        print('no scantime for DMPS or no data for DMPS or no data for GCVI given \nor not defined if scantime is time at the end of the scan or not \nor no file for saving defined')
    else:
        ## set DMPS scan time to the end of the scan (Rackham: adding 6min as scan takes 12min, Madam: adding 4:30min as scan takes 9min)
        DMPSend=DMPS.copy()
        if (scantime_at_end=='No')|(scantime_at_end=='no'):
            DMPSend.index=DMPS.index+pd.Timedelta('%fS'%float(scantime/2))
        
        GCVI=GCVI.asfreq(freq='1S', method='ffill') ## sometimes a second is missing, fill it with the last value
        GCVI=GCVI.assign(count=GCVI.groupby(GCVI.sum_stat.ne(GCVI.sum_stat.shift()).cumsum()).cumcount().add(1))
        GCVI=GCVI.iloc[np.where((GCVI['windtunl']=='Automatc') & (GCVI['sum_stat']==0) & (GCVI['visiblty']>5000))]
        
        DMPSend_C=pd.concat([GCVI,DMPSend.resample('1S').mean()],axis=1)
        DMPSend_C=DMPSend_C.iloc[np.where((DMPSend_C['windtunl']=='Automatc') & (DMPSend_C['sum_stat']==0) & (DMPSend_C['count']>(CVI_ignore+scantime)))]  ## select only time when CVI was off
        DMPSend_C=DMPSend_C.dropna(axis=1,how='all')
        DMPSend_C=DMPSend_C.dropna(subset=['1.500E-8','7.920E-7'],how='all')
        DMPSend_C['event'] = ((DMPSend_C['windtunl']=='Automatc')&(DMPSend_C['sum_stat']==0)&(DMPSend_C['count']>(CVI_ignore+scantime))&((DMPSend_C['count'].diff() < 0.9*scantime)|(DMPSend_C['count'].diff() > 1.1*scantime))).cumsum()
        DMPSend_C=DMPSend_C.join(DMPSend_C.groupby('event').count(), on='event',rsuffix='_r')
        DMPSend_C=DMPSend_C.iloc[:,:50]
        DMPSend_C=DMPSend_C.rename(columns={'visiblty':'event_scan'})
        DMPSend_C.drop(DMPSend_C[DMPSend_C['event_scan'] < CVI_scannumber].index, inplace=True)
        DMPSend_C['event_incl'] = ((DMPSend_C['windtunl']=='Automatc')&(DMPSend_C['sum_stat']==0)&(DMPSend_C['count']>(CVI_ignore+scantime))&((DMPSend_C['count'].diff() < 0.9*scantime)|(DMPSend_C['count'].diff() > 1.1*scantime))).cumsum()
        
        starttime_nofog= []
        endtime_nofog= []
        for key in DMPSend_C.groupby(['event_incl']).mean().index:
            nofog_start = dt.datetime.strptime(str(DMPSend_C.groupby('event_incl').get_group(key).index[0]), '%Y-%m-%d %H:%M:%S')-pd.Timedelta('%iS'%scantime)
            starttime_nofog.append(nofog_start)
            nofog_end = dt.datetime.strptime(str(DMPSend_C.groupby('event_incl').get_group(key).index[-1]), '%Y-%m-%d %H:%M:%S')
            endtime_nofog.append(nofog_end)
        df = pd.DataFrame([DMPSend_C.groupby('event_incl').mean().index,starttime_nofog,endtime_nofog]).transpose()
        df.to_excel('%s.xlsx'%save_to, header=['nofog_nr','starttime_nofog','endtime_nofog'], index=None)
        print(df)

        
#----------------------------------------------------------------
# Function for reading Kevin's CVI data from the Po valley campaign in 1989
def readKevinsCVI(path=None):
    '''     CVI_ALL.CSV  - final CVI results, with invalid results removed
     ISTL_ALL.CSV - interstitial CNC and OPC data
    The time and date are represented as a real number, with the fractional
   part representing the fraction of a day since midnight. The integer part
   is the number of days since January 1, 1900. But to make life easier, all
   you need to know is that MISU's first sampling day was Nov. 10, 1989.
   The time given is the end time of the averaging period (1 minute).
    The first row contains headers for each column of data. The headers are
   almost self-explanatory. The label "Nt" denotes a total aerosol number
   concentration, measured with a CNC. The labels "Na" and "Va" denote
   'accumulation' mode number and volume concentrations, respectively. 
   For the OPC's that we used, the accumulation mode covers the diameter size
   range 0.115-1.0 micrometers. The label "Dgv" denotes the geometric mean
   diameter of the accumulation mode particles, by volume. The label "EF"
   denotes the enrichment factor for the CVI (the raw data have been divided
   by this factor). The label "D50" denotes the 50% cut diameter of the CVI.
    '''
    
    # check if all input is given
    if (path is None):
        print('path as input needed...')

    df = pd.read_csv(path, sep=',', header=0,
                     names=['Endtime','T_amb','p_amb','Nt_istl','Na_istl','Va_istl','Dgv_istl',
                                 'EF1','D50_CV1','Nt_CV1','Na_CV1','Va_CV1','Dgv_CV1','LWC_CV1',
                                  'EF2','D50_CV2','Na_CV2','Va_CV2','Dgv_CV2','LWC_CV2'])
    df['Endtime'] = pd.to_datetime(df["Endtime"]-32822, unit="d",origin=pd.Timestamp('1989-11-10'))
    df.set_index('Endtime', inplace=True,index_name='None')

    return df  


# --------------------------------------------------------------
# Function for reading DMPS data
def readDMPS(path=None,starttime=None,endtime=None,timefmt=None):
    ''' Function to read Rackham DMPS data

    Takes either the argument path = path to data folder as a string
    or flist = a list of paths for chosen data files as strings

    Returns a dictionary with fields: 'time', 'Ntot_int', 'Ntot_cpc',
                                      'dNdlogD', and 'diam'
    '''

    # check if all input is given
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime and timefmt as input needed...')

    flist1 = [f for f in glob.glob(os.path.join(path, "*.sum")) if (f[-7]!='s' and f[-7]!='z' and f[-17]!='b') and (timeselect(f,f[-14:-4],'%Y-%m-%d',starttime,endtime,timefmt))]
    flist2=[f for f in glob.glob(os.path.join(path, "*.sum")) if (f[-7]=='z') and (timeselect(f,f[-23:-13],'%Y-%m-%d',starttime,endtime,timefmt))]
    flist=flist1 + flist2
    flist.sort(key=lambda x: os.path.getmtime(x)) ## sort files in list by changing time if there are several files from same date
    
    # # Main loop
    for file in range(len(flist)):
        if file==0:
            dfs=pd.read_csv(flist[file], sep='\t', header=0)
            # Check for the error with zeros at the end of the diameter array
            if dfs.iloc[0, -1] == 0:
                print('Excluding file: ', flist[file].split('/')[-1], 'because ' +
                      'the last bin diameter is zero')
                dfs=None
                # Wrtie excluded file to log
                with open(path+'/log.txt', 'a') as f:
                    f.write('Excluding file: ' + flist[file].split('/')[-1] +
                            ' because the last bin diameter is zero \n')
                continue

            # Check if the file has too many columns
            if len(dfs.columns) > 40:
                print('Excluding file: ', flist[file].split('/')[-1], 'because ' +
                      'it has more than 40 columns (not standard)')
                dfs=None
                # Write excluded file to log
                with open(path+'/log.txt', 'a') as f:
                    f.write('Excluding file: ' + flist[file].split('/')[-1] + ' because ' +
                      'it has more than 40 columns (not standard)' + '\n')
                continue
            # Set the year to corresponding year
            if (flist[file][-7]=='z'):
                year = dt.datetime(pd.to_datetime(flist[file][-23:-19]).year-1, 12, 31)
            else:
                year = dt.datetime(pd.to_datetime(flist[file][-14:-10]).year-1, 12, 31)
            timestamp = [year + dt.timedelta(item) for item in dfs.iloc[1:, 0]]

            dfs['datetime']=[year + dt.timedelta(item) for item in dfs.iloc[:, 0]]
                
        else:
            # Read data file
            df = pd.read_csv(flist[file], sep='\t', header=0)

            # Check for the error with zeros at the end of the diameter array
            if df.iloc[0, -1] == 0:
                print('Excluding file: ', flist[file].split('/')[-1], 'because' +
                      'the last bin diameter is zero')
                df=None
                # Wrtie excluded file to log
                with open(path+'/log.txt', 'a') as f:
                    f.write('Excluding file: ' + flist[file].split('/')[-1] +
                            ' because the last bin diameter is zero \n')
                continue

            # Check if the file has too many columns
            if len(df.columns) > 40:
                print('Excluding file: ', flist[file].split('/')[-1], 'because' +
                      'it has more than 40 columns (not standard)')
                df=None
                # Write excluded file to log
                with open(path+'/log.txt', 'a') as f:
                    f.write('Excluding file: ' + flist[file].split('/')[-1] + ' because ' +
                      'it has more than 40 columns (not standard)' + '\n')
                continue

            # Print name of data file
            #print(flist[file].split('/')[-1])

            # Set the year to corresponding year
            if (flist[file][-7]=='z'):
                year = dt.datetime(pd.to_datetime(flist[file][-23:-19]).year-1, 12, 31)
            else:
                year = dt.datetime(pd.to_datetime(flist[file][-14:-10]).year-1, 12, 31)
            timestamp = [year + dt.timedelta(item) for item in df.iloc[1:, 0]]

            df['datetime']=[year + dt.timedelta(item) for item in df.iloc[:, 0]]
            dfs=pd.concat([dfs,df])

    # Concatenate data into dataframes
    DMPS = dfs
  
    DMPS.set_index('datetime', inplace=True)
    DMPS=DMPS.iloc[:,1:]
    DMPS.rename(columns={'0.1':'Ntot_int','0.2':'Ntot_cpc'}, inplace=True)
    DMPS=DMPS.loc[starttime:endtime]
    
    return DMPS #if return DMPSdict, header in read_csv has to be changed back to None



# --------------------------------------------------------------
# Function for reading DMPS data
def readDMPS_Linn(path=None,starttime=None,endtime=None,timefmt=None,identifier=None):
    ''' Function to read Rackham DMPS data

    Takes either the argument path = path to data folder as a string
    or flist = a list of paths for chosen data files as strings

    Returns a dictionary with fields: 'time', 'Ntot_int', 'Ntot_cpc',
                                      'dNdlogD', and 'diam'
    '''

    # check if all input is given
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime and timefmt as input needed...')

    flist1 = [f for f in glob.glob(os.path.join(path, "*.sum")) if (f[-7]!='s' and f[-7]!='z' and f[-17]!='b') and (timeselect(f,f[-14:-4],'%Y-%m-%d',starttime,endtime,timefmt))]
    flist2=[f for f in glob.glob(os.path.join(path, "*.sum")) if (f[-7]=='z') and (timeselect(f,f[-23:-13],'%Y-%m-%d',starttime,endtime,timefmt))]
    flist=flist1 + flist2
    flist.sort(key=lambda x: os.path.getmtime(x)) ## sort files in list by changing time if there are several files from same date
    
    
    # # Main loop
    for file in range(len(flist)):
        if file==0:
            dfs=pd.read_csv(flist[file], sep='\t', header=0)
        # Read data file
        df = pd.read_csv(flist[file], sep='\t', header=0)

        # Check for the error with zeros at the end of the diameter array
        if df.iloc[0, -1] == 0:
            print('Excluding file: ', flist[file].split('/')[-1], 'because' +
                  'the last bin diameter is zero')
            # Wrtie excluded file to log
            with open(path+'/log.txt', 'a') as f:
                f.write('Excluding file: ' + flist[file].split('/')[-1] +
                        ' because the last bin diameter is zero \n')
            continue

        # Check if the file has too many columns
        if len(df.columns) > 40:
            print('Excluding file: ', flist[file].split('/')[-1], 'because' +
                  'it has more than 40 columns (not standard)')
            # Write excluded file to log
            with open(path+'/log.txt', 'a') as f:
                f.write('Excluding file: ' + flist[file].split('/')[-1] + ' because ' +
                  'it has more than 40 columns (not standard)' + '\n')
            continue

        # Print name of data file
        #print(flist[file].split('/')[-1])

        # Set the year to corresponding year
        year = dt.datetime(pd.to_datetime(starttime).year-1, 12, 31)
        timestamp = [year + dt.timedelta(item) for item in df.iloc[1:, 0]]

        df['datetime']=[year + dt.timedelta(item) for item in df.iloc[:, 0]]
        dfs=pd.concat([dfs,df])

    # Concatenate data into dataframes
    DMPS = dfs
  
    DMPS.set_index('datetime', inplace=True)
    DMPS=DMPS.iloc[:,1:]
    DMPS.rename(columns={'0.1':'Ntot_int','0.2':'Ntot_cpc'}, inplace=True)
    DMPS=DMPS.loc[starttime:endtime]
    
    return DMPS #if return DMPSdict, header in read_csv has to be changed back to None


# --------------------------------------------------------------
# Function for reading Madam data
def readMadamnew(path=None,starttime=None,endtime=None,timefmt=None,identifier=None):
    ''' Function to read Madam DMPS data

    Takes either the argument path = path to data folder as a string
    or flist = a list of paths for chosen data files as strings

    Returns a dictionary with fields: 'time', 'Ntot_int', 'Ntot_cpc',
                                      'dNdlogD', and 'diam'
    '''

    # check if all input is given
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime and timefmt as input needed...')

    flist1 = [f for f in glob.glob(os.path.join(path, "*.sum")) if (f[-7]!='_') and (timeselect(f,f[-18:-8],'%Y-%m-%d',starttime,endtime,timefmt))]
    flist2=[f for f in glob.glob(os.path.join(path, "*.sum")) if (f[-7]=='_') and (timeselect(f,f[-20:-10],'%Y-%m-%d',starttime,endtime,timefmt))]
    support=[item[:-6]+item[-4:] for item in flist2] ## to delete all A__.sum files where there are A__01.sum,... files that should be used instead
    flist3=[item for item in flist1 if item not in support]
    flist=flist3 + flist2
    flist.sort(key=lambda x: os.path.getmtime(x)) ## sort files in list by changing time if there are several files from same date
    
    dfs = []    
    # # Main loop
    for file in range(len(flist)):
        if file==0:
            dfs=pd.read_csv(flist[file], sep='\t', header=0)
        # Read data file
        df = pd.read_csv(flist[file], sep='\t', header=0)

        # Check for the error with zeros at the end of the diameter array
        if df.iloc[0, -1] == 0:
            print('Excluding file: ', flist[file].split('/')[-1], 'because' +
                  ' the last bin diameter is zero')
            # Wrtie excluded file to log
            with open(path+'/log.txt', 'a') as f:
                f.write('Excluding file: ' + flist[file].split('/')[-1] +
                        ' because the last bin diameter is zero \n')
            continue

        # Check if the file has too few columns
        if len(df.columns) < 4:
            print('Excluding file: ', flist[file].split('/')[-1], 'because' +
                  'it has less than 4 columns (not standard)')
            # Write excluded file to log
            with open(path+'/log.txt', 'a') as f:
                f.write('Excluding file: ' + flist[file].split('/')[-1] + ' because ' +
                  ' it has less than 4 columns (not standard)' + '\n')
            continue
            
        # Check for the error with zeros at the beginning of the diameter array
        if df.columns[3]=='0.0000000E+0.3':
            print('Excluding file: ', flist[file].split('/')[-1], 'because' +
                  'the last bin diameter is zero')
            # Wrtie excluded file to log
            with open(path+'/log.txt', 'a') as f:
                f.write('Excluding file: ' + flist[file].split('/')[-1] +
                        ' because the last bin diameter is zero \n')
            continue


        # Print name of data file
        #print(flist[file].split('/')[-1])

        # Set the year to corresponding year
        year = dt.datetime(pd.to_datetime(starttime).year-1, 12, 31)
        timestamp = [year + dt.timedelta(item) for item in df.iloc[1:, 0]]

        df['datetime']=[year + dt.timedelta(item) for item in df.iloc[:, 0]]
        dfs=dfs.append(df,sort=True)


    # Concatenate data into dataframes
    DMPS = dfs
  
    DMPS.set_index('datetime', inplace=True)
    DMPS=DMPS[~DMPS.index.duplicated(keep='last')]
    DMPS=DMPS.iloc[:,1:]
    DMPS.rename(columns={'0.0000000E+0.1':'Ntot_int','0.0000000E+0.2':'Ntot_cpc'}, inplace=True)
    DMPS=DMPS.loc[starttime:endtime]
    
    #sort Dps
    DMPSnew=DMPS[sorted(DMPS.columns[2:], key=lambda x: float(x))]
    DMPSnew.insert(0, 'Ntot_int', DMPS['Ntot_int'])
    DMPSnew.insert(1, 'Ntot_cpc', DMPS['Ntot_cpc'])
    
    return DMPSnew #if return DMPSdict, header in read_csv has to be changed back to None





def readDMPSLinn(path=None,starttime=None,endtime=None,timefmt=None,identifier=None):
    ''' Function to read Rackham DMPS data (BUT doesn't work if there are several files from the same date...)

    Takes either the argument path = path to data folder as a string
    or flist = a list of paths for chosen data files as strings

    Returns a dictionary with fields: 'time', 'Ntot_int', 'Ntot_cpc',
                                      'dNdlogD', and 'diam'
    '''

    # check if all input is given
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime and timefmt as input needed...')

    flist = [f for f in glob.glob(os.path.join(path, "*.sum")) if (f[-7]!='s' and f[-7]!='z' and f[-17]!='b') and (timeselect(f,f[-14:-4],'%Y-%m-%d',starttime,endtime,timefmt))]
    flist.sort(key=lambda x: os.path.getmtime(x)) ## sort files in list by changing time if there are several files from same date
    print(flist)

    # Create lists
    time = []
    Ntot_int = []
    Ntot_cpc = []
    dNdlogD = []
    diam = []
    dfs = []

    # # Main loop
    for file in range(len(flist)):
        # Read data file
        df = pd.read_csv(flist[file], sep='\t', header=0)

        # Check for the error with zeros at the end of the diameter array
        if df.iloc[0, -1] == 0:
            print('Excluding file: ', flist[file].split('/')[-1], 'because' +
                  'the last bin diameter is zero')
            # Wrtie excluded file to log
            with open(path+'/log.txt', 'a') as f:
                f.write('Excluding file: ' + flist[file].split('/')[-1] +
                        ' because the last bin diameter is zero \n')
            continue

        # Check if the file has too many columns
        if len(df.columns) > 40:
            print('Excluding file: ', flist[file].split('/')[-1], 'because' +
                  'it has more than 40 columns (not standard)')
            # Write excluded file to log
            with open(path+'/log.txt', 'a') as f:
                f.write('Excluding file: ' + flist[file].split('/')[-1] + ' because ' +
                  'it has more than 40 columns (not standard)' + '\n')
            continue

        # Print name of data file
        #print(flist[file].split('/')[-1])

        # Set the year to corresponding year
        year = dt.datetime(pd.to_datetime(starttime).year-1, 12, 31)
        timestamp = [year + dt.timedelta(item) for item in df.iloc[1:, 0]]

        # Append data to lists
        time.append(pd.DataFrame(timestamp))
        Ntot_int.append(pd.DataFrame(df.iloc[1:, 1].values, index=timestamp))
        Ntot_cpc.append(pd.DataFrame(df.iloc[1:, 2].values, index=timestamp))
        dNdlogD.append(pd.DataFrame(df.iloc[1:, 3:].values, index=timestamp,
                                    columns=df.iloc[0, 3:].values))
        diam.append(pd.DataFrame(np.tile(df.iloc[0, 3:].values,
                                         (df.shape[0]-1, 1)), index=timestamp))
        
        df['datetime']=[year + dt.timedelta(item) for item in df.iloc[:, 0]]
        dfs.append(df)

    # Concatenate data into dataframes
    time = pd.concat(time)
    Ntot_int = pd.concat(Ntot_int)
    Ntot_cpc = pd.concat(Ntot_cpc)
    dNdlogD = pd.concat(dNdlogD)
    diam = pd.concat(diam)
    DMPS = pd.concat(dfs)

    # Return data as a dictionary of pandas DataFrame objects
    DMPSdict = {'time': time.reset_index(drop=True),
            'Ntot_int': Ntot_int,
            'Ntot_cpc': Ntot_cpc,
            'dNdlogD': dNdlogD,
            'diam': diam}
  
    DMPS.set_index('datetime', inplace=True)
    DMPS=DMPS.iloc[:,1:]
    DMPS.rename(columns={'0.1':'Ntot_int','0.2':'Ntot_cpc'}, inplace=True)
    DMPS=DMPS.loc[starttime:endtime]
    
    return DMPS #if return DMPSdict, header in read_csv has to be changed back to None


def readrawRackham(path=None,starttime=None,endtime=None,timefmt=None):
    ''' Function for reading raw Rackham data

    Takes either the argument path = path to data folder as a string
    or flist = a list of paths for chosen data files as strings

    Returns a pandas DataFrame
    '''
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime and timefmt as input needed...')

    flist = [f for f in glob.glob(os.path.join(path, "*.stp")) if (timeselect(f,f[-14:-4],'%Y-%m-%d',starttime,endtime,timefmt))]

    # Empty list to fill with dfs
    Rackham_raw = []

    for i, file in enumerate(flist):
	# Read file
        df = pd.read_csv(file, sep='\t,|,\t',header=0)

        # Make datetime index and drop those columns (plus the weird empty column)
        df.index = pd.to_datetime(df['Date']+' '+df['Time'], format='%Y-%m-%d %H:%M:%S')
        df.drop(['Date','Time'], axis=1, inplace=True)

	# Append dfs to list
        Rackham_raw.append(df)

    # Concatenate dfs
    Rackham_raw = pd.concat(Rackham_raw) 
    Rackham_raw = Rackham_raw.sort_index()[~Rackham_raw.index.duplicated(keep='first')]
    
    Rackham_raw=Rackham_raw.loc[starttime:endtime]
    
    return Rackham_raw



def readrawscnRackham(path=None,starttime=None,endtime=None,timefmt=None):
    ''' Function for reading raw Rackham data

    Takes either the argument path = path to data folder as a string
    or flist = a list of paths for chosen data files as strings

    Returns a pandas DataFrame
    '''
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime and timefmt as input needed...')

    flist = [f for f in glob.glob(os.path.join(path, "ACES_LAB-1-Andi_n1-*.scn")) if (timeselect(f,f[-14:-4],'%Y-%m-%d',starttime,endtime,timefmt))]

    # Empty list to fill with dfs
    Rackham_raw = []

    for i, file in enumerate(flist):
	# Read file
        df = pd.read_csv(file,skiprows=2,header=0, names=['Date','Time','BPS-01','BPS-02','DPS-01','MFM-01','RHT-RH-01','RHT-T-01','RHT-RH-02','RHT-T-02','HV-01','CPC1Puls','CPC2Puls'], sep=',\t|\t|,')

        # Make datetime index and drop those columns (plus the weird empty column)
        df.index = pd.to_datetime(df['Date']+' '+df['Time'], format='%Y-%m-%d %H:%M:%S')
        df.drop(['Date','Time'], axis=1, inplace=True)

	# Append dfs to list
        Rackham_raw.append(df)

    # Concatenate dfs
    Rackham_raw = pd.concat(Rackham_raw)  
    
    Rackham_raw=Rackham_raw.loc[starttime:endtime]
    
    return Rackham_raw



def readMadam(path=None,starttime=None,endtime=None,timefmt=None,identifier='CPC1'):
    ''' Function to read Madam data

    Takes either the argument path = path to data folder as a string
    or flist = a list of paths for chosen data files as strings

    Returns a dictionary
    '''

    # check if all input is given
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime, timefmt, and identifier as input needed...')

    flist = [f for f in glob2.glob(path+'/2xloggfile_'+identifier+'*.dat') if timeselect(f,f[-14:-4],'%Y-%m-%d',starttime,endtime,timefmt)]

    # Initialise DataFrame list
    dfs = []

    # # Loop for reading the data files
    #print('Reading data...')
    for file in range(len(flist)):
        # Read data file
        df = pd.read_csv(flist[file],sep='\t', index_col=None, skiprows=0,header=0)

        df['CPCtime']=df['CPCtime'].str.zfill(np.max(df['CPCtime'].str.len()))
        df=df.iloc[61:] ## dirty way of getting rid of the last day
        df.index=pd.to_datetime(flist[file][-14:-4]+' '+df.CPCtime,format='%Y-%m-%d %H%M%S.%f',errors='coerce')
        df.index.name='datetime'
        
        df['scantime']=np.where(df.iloc[:,0]=='ScanStart',df['CPCtime'],np.nan)
        df['scantime']=df['scantime'].ffill(axis = 0)
        df['scantime']=pd.to_datetime(flist[file][-14:-4]+' '+df.scantime,format='%Y-%m-%d %H%M%S.%f',errors='coerce')
        
        df=df.mask(df.iloc[:,3]=='CPCtime') # delete all rows with text (every 47th row new cycle starts), better?: Madam2 = Madam2[Madam2.ne(Madam2.columns).any(1)]
        df=df.iloc[:,3:] # delete first columns with text

        df=df.loc[df.index.dropna()]

        # Append to list of dfs
        dfs.append(df)

        # Print name of data file
        #print(flist[file].split('/')[-1])

    # Concatenate the df list to single df
    #print('Concatenating DataFrames...')
    Madam = pd.concat(dfs)
    Madam[Madam.columns[0:-1]] = Madam.iloc[:, 0:-1].astype('float64')
    
    Madam=Madam.loc[starttime:endtime]
    
    return Madam



def readCPCMadam(path=None,starttime=None,endtime=None,timefmt=None,identifier='CPC2'):
    ''' Function for reading Madams total CPC data

    Input path, starttime, endtime, and timefmt as strings

    Returns a pandas DataFrame with the chosen fields (see code)
    '''    
# check if all input is given
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime and timefmt as input needed...')

    flist = [f for f in glob2.glob(path+'/2xloggfile_'+identifier+'*.dat') if timeselect(f,f[-14:-4],'%Y-%m-%d',starttime,endtime,timefmt) and f[-16]!='s']
    
    # Define file header
    head = ['date', 'time', 'a', 'Ntot_cpc_M', 'b', 'c']

    # Initialise DataFrame list
    dfs = []

    # # Loop for reading the data files
    #print('Reading data...')
    for file in range(len(flist)):
        # Read data file
        df = pd.read_csv(flist[file], sep='\t', header=None, names=head)

        # Append to list of dfs
        dfs.append(df)

        # Print name of data file
        #print(flist[file].split('/')[-1])

    # Concatenate the df list to single df
    #print('Concatenating DataFrames...')
    CPC_Madam = pd.concat(dfs)

    # Put together date & time columns as 'time' and drop 'date'
    #print('Combining date and time...')
    CPC_Madam.index = pd.to_datetime(CPC_Madam.date+' '+CPC_Madam.time, format='%Y-%m-%d %H:%M:%S')
    CPC_Madam.index.names = ['datetime']

    
    CPC_Madam=CPC_Madam.loc[starttime:endtime]
    
    return CPC_Madam


def readCPC1sMadam(path=None,starttime=None,endtime=None,timefmt=None,identifier='CPC2'):
    ''' Function for reading Madams total CPC data

    Input path, starttime, endtime, and timefmt as strings

    Returns a pandas DataFrame with the chosen fields (see code)
    '''    
# check if all input is given
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime and timefmt as input needed...')

    flist = [f for f in glob2.glob(path+'/2xloggfile_'+identifier+'*.dat') if timeselect(f,f[-14:-4],'%Y-%m-%d',starttime,endtime,timefmt) and f[-16]=='s']
    
    # Define file header
    head = ['date', 'time', 'Ntot']

    # Initialise DataFrame list
    dfs = []

    # # Loop for reading the data files
    #print('Reading data...')
    for file in range(len(flist)):
        # Read data file
        df = pd.read_csv(flist[file], sep='\t', header=None, names=head,skiprows=1)

        # Append to list of dfs
        dfs.append(df)

        # Print name of data file
        #print(flist[file].split('/')[-1])

    # Concatenate the df list to single df
    #print('Concatenating DataFrames...')
    CPC_Madam = pd.concat(dfs)

    # Put together date & time columns as 'time' and drop 'date'
    #print('Combining date and time...')
    CPC_Madam.index = pd.to_datetime(CPC_Madam.date+' '+CPC_Madam.time, format='%Y-%m-%d %H:%M:%S')
    CPC_Madam.index.names = ['datetime']

    
    CPC_Madam=CPC_Madam.loc[starttime:endtime]
    
    return CPC_Madam


def readDMAMadam(path=None,starttime=None,endtime=None,timefmt=None,identifier='CPC1',timeshift=None):
    ''' Function to read Madam's DMA datafile data

    Takes either the argument path = path to data folder as a string
    or flist = a list of paths for chosen data files as strings

    Returns a dictionary
    '''

    # check if all input is given
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime, timefmt, and identifier as input needed...')

    flist = [f for f in glob2.glob(path+'/2xdatafile_'+identifier+'*.dat') if timeselect(f,f[-14:-4],'%Y-%m-%d',starttime,endtime,timefmt)]
    # Initialise DataFrame list
    dfs = []

    # # Loop for reading the data files
    #print('Reading data...')
    for file in range(len(flist)):
        # Read data file
        df = pd.read_csv(flist[file],sep='\t',na_values='-999', index_col=None, skiprows=0,header=None,names=(10**np.arange(0,3,0.05)*10**(-9)))
        df['scantime']=np.where(df.iloc[:,0].str[0:9]=='ScanStart',df.iloc[:,0].str[10:],np.nan)
        df['scantime']=df['scantime'].ffill(axis = 0)
        if timeshift!=None:
            df['scantime']=pd.to_datetime(df['scantime'],format='%Y%m%d %H%M%S.%f',errors='coerce')-pd.Timedelta('%s'%timeshift)
        else:
            df['scantime']=pd.to_datetime(df['scantime'],format='%Y%m%d %H%M%S.%f',errors='coerce')
        
        df=df.mask(df.iloc[:,0].str[0:9]=='ScanStart') # delete all rows with text (every 47th row new cycle starts), better?: Madam2 = Madam2[Madam2.ne(Madam2.columns).any(1)]

        df.index=df['scantime']
        df.index.name='datetime'
        #df=df.loc[df.index.dropna()]

        # Append to list of dfs
        dfs.append(df)

        # Print name of data file
        #print(flist[file].split('/')[-1])

    # Concatenate the df list to single df
    #print('Concatenating DataFrames...')
    Madam = pd.concat(dfs)
    #only keep 3rd and 4th row (where the resolution is 60 bins)
    Madam=Madam.groupby('datetime').nth([-2,-1])
    #set down scan start time as time between two upscans
    Madam['calc_time']=Madam.index-(Madam.index-Madam['scantime'].shift(periods=-1))/2
    Madam[Madam.columns[0:-2]] = Madam.iloc[:, 0:-2].astype('float64')
    Madam=Madam.replace(-999,np.nan)
    Madam=Madam.loc[starttime:endtime]
    
    return Madam



#-------------------------------------------------------------- 


def readCPCCVI(path=None,starttime=None,endtime=None,timefmt=None):
    ''' Function for reading CPC-CVI data

    Input path, starttime, endtime, and timefmt as strings

    Returns a pandas DataFrame with the chosen fields (see code)
    '''    
# check if all input is given
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime and timefmt as input needed...')

    flist = [f for f in glob.glob(os.path.join(path, "*CPC_3010*.scn")) if timeselect(f,f[-14:-4],'%Y-%m-%d',starttime,endtime,timefmt)]
    
    
    # Define file header
    head = ['date', 'time', 'CPC_N']

    # Initialise DataFrame list
    dfs = []

    # # Loop for reading the data files
    #print('Reading data...')
    for file in range(len(flist)):
        # Read data file
        df = pd.read_csv(flist[file], sep=',\t', header=None, names=head)

        # Append to list of dfs
        dfs.append(df)

        # Print name of data file
        #print(flist[file].split('/')[-1])

    # Concatenate the df list to single df
    #print('Concatenating DataFrames...')
    CPC_CVI = pd.concat(dfs)

    # Put together date & time columns as 'time' and drop 'date'
    #print('Combining date and time...')
    CPC_CVI.time = pd.to_datetime(CPC_CVI.date+' '+CPC_CVI.time, format='%Y-%m-%d %H:%M:%S')
    CPC_CVI.drop('date', axis=1, inplace=True)

    CPC_CVIout = CPC_CVI.loc[:, ['time', 'CPC_N']]
    CPC_CVIout = CPC_CVIout.reset_index(drop=True)
    CPC_CVIout.set_index('time', inplace=True)
    CPC_CVIout.index.names = ['datetime']

    CPC_CVIout=CPC_CVIout.loc[starttime:endtime]
    
    return CPC_CVIout

# -----------------------------------------------------------------------------
def readCPCPM1(path=None,starttime=None,endtime=None,timefmt=None):
    ''' Function for reading CPC-CVI data

    Input path, starttime, endtime, and timefmt as strings

    Returns a pandas DataFrame with the chosen fields (see code)
    '''    
# check if all input is given
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime and timefmt as input needed...')

    flist = [f for f in glob.glob(os.path.join(path, "*CPC_3010*.scn")) if timeselect(f,f[-14:-4],'%Y-%m-%d',starttime,endtime,timefmt)]
    
    
    # Define file header
    head = ['date', 'time', 'CPC_N']

    # Initialise DataFrame list
    dfs = []

    # # Loop for reading the data files
    #print('Reading data...')
    for file in range(len(flist)):
        # Read data file
        df = pd.read_csv(flist[file], sep=',\t', header=None, names=head)

        # Append to list of dfs
        dfs.append(df)

        # Print name of data file
        #print(flist[file].split('/')[-1])

    # Concatenate the df list to single df
    #print('Concatenating DataFrames...')
    CPC_CVI = pd.concat(dfs)

    # Put together date & time columns as 'time' and drop 'date'
    #print('Combining date and time...')
    CPC_CVI.time = pd.to_datetime(CPC_CVI.date+' '+CPC_CVI.time, format='%Y-%m-%d %H:%M:%S')
    CPC_CVI.drop('date', axis=1, inplace=True)

    CPC_CVIout = CPC_CVI.loc[:, ['time', 'CPC_N']]
    CPC_CVIout = CPC_CVIout.reset_index(drop=True)
    CPC_CVIout.set_index('time', inplace=True)
    CPC_CVIout.index.names = ['datetime']

    CPC_CVIout=CPC_CVIout.loc[starttime:endtime]
    
    return CPC_CVIout




# -----------------------------------------------------------------------------

def readMCPC(path=None,starttime=None,endtime=None,timefmt=None):
    ''' Function for reading MCPC data

    Input path, starttime, endtime, and timefmt as strings

    Returns a pandas DataFrame with the chosen fields (see code)
    '''    
# check if all input is given
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime and timefmt as input needed...')

    flist = [f for f in glob2.glob(path+'*.txt') if timeselect(f,f[-12:-6],'%y%m%d',starttime,endtime,timefmt)]

    
    # Define file header
    #head = ['date', 'time', 'a', 'Ntot_cpc_M', 'b', 'c']

    # Initialise DataFrame list
    dfs = []

    # # Loop for reading the data files
    #print('Reading data...')
    for file in range(len(flist)):
        # Read data file
        df = pd.read_csv(flist[file], sep='\t', header=0, skiprows=14)

        # Append to list of dfs
        dfs.append(df)

        # Print name of data file
        #print(flist[file].split('/')[-1])

    # Concatenate the df list to single df
    #print('Concatenating DataFrames...')
    MCPC = pd.concat(dfs)

    # Put together date & time columns as 'time' and drop 'date'
    #print('Combining date and time...')
    MCPC['datetime']=MCPC['#YY/MM/DD'].astype(str) + ' ' + MCPC['HR:MN:SC'].astype(str)
    MCPC.index=pd.to_datetime(MCPC['datetime'],format='%y/%m/%d %H:%M:%S')
    MCPC=MCPC.drop(columns=['datetime'])
    MCPC.index.names = ['datetime']
    
    MCPC=MCPC.loc[starttime:endtime]
    
    return MCPC

# -----------------------------------------------------------------------

def readSEMSDp(path=None,starttime=None,endtime=None,timefmt=None,identifier='1'):
    ''' Function for reading SEMS data

    Input path, starttime, endtime, and timefmt as strings

    Returns a pandas DataFrame with the chosen fields (see code)
    '''    
# check if all input is given
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime and timefmt as input needed...')

    flist = [f for f in glob.glob(os.path.join(path,'SEMS%s/Data/*/*_RESULTS_*'%identifier)) if timeselect(f,f[-17:-11],'%y%m%d',starttime,endtime,timefmt)]    
    
    # Initialise DataFrame list
    dfs = []
    dfs_final = []

    # # Loop for reading the data files
    #print('Reading data...')
    for file in range(len(flist)):
        # Read data file pd.read_csv(path_SEMS1, skiprows=8, header=0)
        trash=pd.read_csv(flist[file], header=0, skiprows=8)
        if str(trash.iloc[0])[46]=='\n':
            Dmax=float(str(trash.iloc[0])[43:46])
        else:
            Dmax=float(str(trash.iloc[0])[43:45])
        if str(trash.iloc[1])[45]=='\n':
            Dmin=float(str(trash.iloc[1])[43:45])
        else:
            Dmin=float(str(trash.iloc[1])[43:46])
        nbins=int(str(trash.iloc[2])[34:36])
        del trash
        print(Dmin,Dmax,nbins)
        
        df = pd.read_csv(flist[file], sep='\t', header=0, skiprows=55-int(identifier))
        df['datetime']=df['#StartDate'].astype(str) + ' ' + df['StartTime'].astype(str)
        df['scan_start']=pd.to_datetime(df['#StartDate'].astype(str) + ' ' + df['StartTime'].astype(str),format='%y%m%d %H:%M:%S')
        df['scan_end']=pd.to_datetime(df['EndDate'].astype(str) + ' ' + df['EndTime'].astype(str),format='%y%m%d %H:%M:%S')
        df.index=pd.to_datetime(df['datetime'],format='%y%m%d %H:%M:%S')#-pd.Timedelta('1S')
        df=df.drop(columns=['datetime'])
        
        df_final=pd.DataFrame(index=range(len(df)*nbins),
            columns=['datetime','Dp','dNdlogDp','dlogDp','Nconc'])
        for i in np.linspace(0,len(df)-1,len(df)):
            i=int(i)
            for n in np.linspace(0,nbins-1,nbins):
                n=int(n)
                df_final.iloc[i*nbins+n,0]=df['scan_start'][i]+pd.Timedelta('%fS'%(n*(df['scan_end'][i]-df['scan_start'][i]).total_seconds()/nbins))
                if i%2==0:
                    df_final.iloc[i*nbins+n,1]=df['Bin_Dia%i'%(n+1)][i]
                else:
                    df_final.iloc[i*nbins+n,1]=df['Bin_Dia%i'%(nbins-n)][i]
                if i%2==0:
                    df_final.iloc[i*nbins+n,2]=df['Bin_Conc%i'%(n+1)][i]
                else:
                    df_final.iloc[i*nbins+n,2]=df['Bin_Conc%i'%(nbins-n)][i]
                if n==0:
                    df_final.iloc[i*nbins+n,3]=np.log10(df_final.iloc[i*nbins+n,1].astype('float'))-np.log10(Dmin-2)
                else:
                    df_final.iloc[i*nbins+n,3]=np.log10(df_final.iloc[i*nbins+n-1,1].astype('float'))
                df_final.iloc[i*nbins+n,4]=df_final.iloc[i*nbins+n,2].astype('float')*df_final.iloc[i*nbins+n,3].astype('float')
        # Append to list of dfs
        dfs_final.append(df_final)

        # Print name of data file
        #print(flist[file].split('/')[-1])

    # Concatenate the df list to single df
    #print('Concatenating DataFrames...')
    SEMS = pd.concat(dfs_final)
    SEMS.index=SEMS.iloc[:,0]
    SEMS['Dp']=SEMS['Dp'].astype('float')
    SEMS['Nconc']=SEMS['Nconc'].astype('float')
    
    SEMS=SEMS.loc[starttime:endtime]
    return SEMS


# -----------------------------------------------------------------------

def readSEMS(path=None,starttime=None,endtime=None,timefmt=None,identifier='1'):
    ''' Function for reading SEMS data

    Input path, starttime, endtime, and timefmt as strings

    Returns a pandas DataFrame with the chosen fields (see code)
    '''    
# check if all input is given
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime and timefmt as input needed...')

    flist = [f for f in glob.glob(os.path.join(path,'SEMS%s/Data/*/*_RESULTS_*'%identifier)) if timeselect(f,f[-17:-11],'%y%m%d',starttime,endtime,timefmt)]    
    
    # Initialise DataFrame list
    dfs = []

    # # Loop for reading the data files
    #print('Reading data...')
    for file in range(len(flist)):
        df = pd.read_csv(flist[file], sep='\t', header=0, skiprows=55-int(identifier))
        df['datetime']=df['#StartDate'].astype(str) + ' ' + df['StartTime'].astype(str)
        df['scan_start']=pd.to_datetime(df['#StartDate'].astype(str) + ' ' + df['StartTime'].astype(str),format='%y%m%d %H:%M:%S')
        df['scan_end']=pd.to_datetime(df['EndDate'].astype(str) + ' ' + df['EndTime'].astype(str),format='%y%m%d %H:%M:%S')
        df.index=pd.to_datetime(df['datetime'],format='%y%m%d %H:%M:%S')#-pd.Timedelta('1S')
        df=df.drop(columns=['datetime'])
        
        # Append to list of dfs
        dfs.append(df)

        # Print name of data file
        #print(flist[file].split('/')[-1])

    # Concatenate the df list to single df
    #print('Concatenating DataFrames...')
    SEMS = pd.concat(dfs)
    
    SEMS=SEMS.loc[starttime:endtime]
    return SEMS


# -----------------------------------------------------------------------

# Simplified function for reading GCVI data
def readGCVI(path=None,path_CVISD=None,starttime=None,endtime=None,timefmt=None):
    ''' Function for reading GCVI and CVI data

    Arguments
                path : string (path to data folder)

    Returns three pandas DataFrames (GCVI, CVI, CVI-SD) with the chosen fields (see code)
    '''
    # Make list of files
    G_flist = [f for f in glob.glob(os.path.join(path, "**/GCVI*.dat")) if timeselect(f,f[-17:-11],'%y%m%d',starttime,endtime,timefmt)]
    ###G_flist = glob2.glob(path+'**/GCVI*.dat')
    ###G_flist.sort()

    C_flist = [f for f in glob.glob(os.path.join(path, "**/CVI*.dat")) if timeselect(f,f[-17:-11],'%y%m%d',starttime,endtime,timefmt)]
    ###C_flist = glob2.glob(path+'**/CVI*.dat')
    ###C_flist.sort()
    
    CSD_flist = [f for f in glob.glob(os.path.join(path_CVISD, "*.txt")) if timeselect(f,f[-12:-6],'%y%m%d',starttime,endtime,timefmt)]

    # Define headers for the different files
    GCVI_head = ['date', 'time', 'visiblty', 'cloudstt', 'precstat',
                 'airspeed', 'humidity', 'temperat', 'covertmp', 'coverpwr',
                 'uppertmp', 'upperpwr', 'lowertmp', 'lowerpwr', 'vis_xmit',
                 'vis_recv', 'cvi_stat', 'compstat', 'vac_stat', 'blwrstat',
                 'blwr_pwr', 'de_icing', 'windtunl', 'airspdsp', 'covertsp',
                 'uppertsp', 'lowertsp', 'rhthresh', 'precsens', 'ignrprec',
                 'visthrsh', 'err_rprt', 'savedata']

    CVI_head = ['date', 'time', 'cnt_flow', 'cntflprs', 'cntfltmp', 'cnthtpwr',
                'instflow', 'tosmflow', 'lfe_flow', 'lfe_temp', 'cut_size',
                'airspeed', 'oat_temp', 'add_flow', 'addflwsp', 'addflwtm',
                'addflwpr', 'xs_flow', 'xsflowsp', 'xsflowtm', 'xsflowpr',
                'conetemp', 'cone_pwr', 'pylontmp', 'pylonpwr', 'sensrtmp',
                'sensrpwr', 'cntflwsp', 'cnttmpsp', 'tosmflsp', 'conetmsp',
                'pylntmsp', 'err_rprt', 'airspsrc', 'oatmpsrc', 'flwcntrl',
                'htrcntrl', 'de_icing', 'manl_mfc', 'savedata']
    
    CVISD_head = ['date', 'time', 'cnt_flow', 'cntflprs', 'cntfltmp', 'cnthtpwr',
                'instflow', 'tosmflow', 'lfe_flow', 'lfe_temp', 'cut_size',
                'airspeed', 'oat_temp', 'add_flow', 'addflwsp', 'addflwtm',
                'addflwpr', 'xs_flow', 'xsflowsp', 'xsflowtm', 'xsflowpr',
                'conetemp', 'cone_pwr', 'pylontmp', 'pylonpwr', 'sensrtmp',
                'sensrpwr', 'cntflwsp', 'cnttmpsp', 'tosmflsp', 'conetmsp',
                'pylntmsp', 'err_rprt', 'airspsrc', 'oatmpsrc', 'flwcntrl',
                'htrcntrl', 'de_icing', 'manl_mfc']


    # Initialise DataFrame lists
    GCVIdfs = []
    CVIdfs = []
    CVISDdfs = []

    #Choose which fields to output
    print('Choosing fields...')
    GCVI_wantedcols = ['date', 'time', 'visiblty','humidity', 'temperat','airspeed',
                       'cvi_stat', 'compstat', 'vac_stat', 'blwrstat',
                       'blwr_pwr', 'windtunl']
    CVI_wantedcols = ['date', 'time','cnt_flow', 'cntfltmp', 'instflow', 'tosmflow', 'add_flow', 'xs_flow', 'cut_size', 'airspeed']
    CVISD_wantedcols = ['date', 'time', 'instflow', 'tosmflow', 'xs_flow', 'cut_size', 'airspeed']

    # # Loop for reading the data files
    print('Reading data...')
    for file in range(len(G_flist)):
        # Read GCVI data
        GCVI_tmp = pd.read_csv(G_flist[file], sep='\t', skiprows=8,
                               header=None, names=GCVI_head, decimal='.') # CHANGED FROM , TO .
        # Append to list of GCVI dfs
        GCVIdfs.append(GCVI_tmp[GCVI_wantedcols])
        # Print which file was just read
        print(G_flist[file].split('/')[-1])

    for file in range(len(C_flist)): # ADDED THIS TO FIX DIFF. NO. OF FILES ISSUE
        # Read CVI data
        CVI_tmp = pd.read_csv(C_flist[file], sep='\t', skiprows=11,
                              header=None, names=CVI_head, decimal='.') # CHANGED FROM , TO .
        # Append to list of CVI dfs
        CVIdfs.append(CVI_tmp[CVI_wantedcols])
        # Print which file was just read
        print(C_flist[file].split('/')[-1])

    for file in range(len(CSD_flist)): # ADDED THIS TO FIX DIFF. NO. OF FILES ISSUE
        # Read CVISD data
        CVISD_tmp = pd.read_csv(CSD_flist[file], sep='\t| \t|  \t', skiprows=11,
                              header=None, index_col=False,names=CVISD_head, decimal='.') # CHANGED FROM , TO .
        # Append to list of CVISD dfs
        CVISDdfs.append(CVISD_tmp[CVISD_wantedcols])
        # Print which file was just read
        print(CSD_flist[file].split('/')[-1])
    
        
    # Delete the temporary files
    del GCVI_tmp
    if C_flist!=[]:
        del CVI_tmp
    if CSD_flist!=[]:
        del CVISD_tmp

    # Concatenate the df lists to single dfs
    print('Concatenating DataFrames...')
    GCVI = pd.concat(GCVIdfs)
    if C_flist!=[]:
        CVI = pd.concat(CVIdfs)
    if CSD_flist!=[]:
        CVISD = pd.concat(CVISDdfs)
        

    # # Make the final output DataFrames
    # Replace On/Off with 1/0
    print('Replacing On/Off strings with 1/0...')
    repdict = {'On': 1., 'Off': 0.}
    repdict2 = {'Yes': 1, 'No': 0}
    GCVI['cvi_stat'] = GCVI['cvi_stat'].map(repdict)
    GCVI['compstat'] = GCVI['compstat'].map(repdict)
    GCVI['vac_stat'] = GCVI['vac_stat'].map(repdict)
    GCVI['blwrstat'] = GCVI['blwrstat'].map(repdict)
    GCVI.reset_index(inplace=True, drop=True)


    # Make the status sum
    print('Calculating status sum...')
    GCVI = GCVI.assign(sum_stat=GCVI.cvi_stat + GCVI.compstat +\
                       GCVI.vac_stat + GCVI.blwrstat)

    # Make sure shit is numeric
    if C_flist!=[]:
        CVI.tosmflow = pd.to_numeric(CVI.tosmflow)
        CVI.cut_size = pd.to_numeric(CVI.cut_size)
        CVI.airspeed = pd.to_numeric(CVI.airspeed)
    if CSD_flist!=[]:
        CVISD.tosmflow = pd.to_numeric(CVISD.tosmflow)
        CVISD.cut_size = pd.to_numeric(CVISD.cut_size)
        CVISD.airspeed = pd.to_numeric(CVISD.airspeed)
    GCVI.airspeed = pd.to_numeric(GCVI.airspeed)
    GCVI.visiblty = pd.to_numeric(GCVI.visiblty)

    # Put together date & time columns as 'time' and drop 'date' !! changed it so that it now is done before EF calculation
    print('Combining date and time...')
    GCVI.time = pd.to_datetime(GCVI.date.values+' '+GCVI.time.values,
                               format='%y/%m/%d %H:%M:%S')
    GCVI.drop('date', axis=1, inplace=True)

    if C_flist!=[]:
        CVI.time = pd.to_datetime(CVI.date.values+' '+CVI.time.values,
                                  format='%y/%m/%d %H:%M:%S')
        CVI.drop('date', axis=1, inplace=True)

    if CSD_flist!=[]:
        CVISD.time = pd.to_datetime(CVISD.date+' '+CVISD.time,
                              format='%y/%m/%d %H:%M:%S')
        CVISD.drop('date', axis=1, inplace=True)

    # Set time as index
    GCVI.set_index('time', inplace=True)
    if C_flist!=[]:
        CVI.set_index('time', inplace=True)
    if CSD_flist!=[]:
        CVISD.set_index('time', inplace=True)
    
    # Calculate enrichment factor
    print('Calculating enrichment factor...')
    if C_flist!=[]:
        CVI = CVI.assign(EF=CVI.airspeed * 1.67e-5 * 60 / (CVI.tosmflow * 0.001))
    #CVI = CVI.assign(EF_blwr=GCVI.loc[CVI.index, 'blwr_pwr'] * 0.614 * 1.67e-5 * 60 / (CVI.tosmflow * 0.001)) #before: CVI.assign(EF_blwr=GCVI.loc[CVI.index, 'blwr_pwr']...
        EF_mix = CVI.EF.copy()
    #EF_mix[GCVI.windtunl == 'Man'] = CVI.EF_blwr[GCVI.windtunl == 'Man']
    #CVI = CVI.assign(EF_mix=EF_mix)
    
    if CSD_flist!=[]:
        CVISD = CVISD.assign(EFSD=CVISD.airspeed * 1.67e-5 * 60 / (CVISD.tosmflow * 0.001))
    #CVISD = CVISD.assign(EFSD_blwr=GCVI.loc[CVISD.index, 'blwr_pwr'] * 0.614 * 1.67e-5 * 60 / (CVISD.tosmflow * 0.001)) #before: CVI.assign(EF_blwr=GCVI.loc[CVI.index, 'blwr_pwr']...
    if CSD_flist!=[]:
        EFSD_mix = CVISD.EFSD.copy()
    #EFSD_mix[GCVI.windtunl == 'Man'] = CVISD.EFSD_blwr[GCVI.windtunl == 'Man']
    #CVISD = CVISD.assign(EFSD_mix=EFSD_mix)
    
    GCVI['sum_stat_ext']=np.where((GCVI['windtunl']=='Automatc') & (GCVI['sum_stat']>0) & (GCVI['sum_stat']<4),2,np.nan) ## as a definition for 'switching' (not completely on or off)
    
    print('Finished data processing')
    
    GCVI=GCVI.loc[starttime:endtime]
    if C_flist!=[]:
        CVI=CVI.loc[starttime:endtime]
    else:
        CVI=pd.DataFrame()        
    if CSD_flist!=[]:
        CVISD=CVISD.loc[starttime:endtime]
    else:
        CVISD=pd.DataFrame()

    return GCVI, CVI, CVISD
# -----------------------------------------------------------------------

# Simplified function for reading GCVI data
def readGCVI_v2_0(path=None,path_CVISD=None,starttime=None,endtime=None,timefmt=None):
    ''' Function for reading GCVI and CVI data

    Arguments
                path : string (path to data folder)

    Returns three pandas DataFrames (GCVI, CVI, CVI-SD) with the chosen fields (see code)
    '''
    # Make list of files
    G_flist = [f for f in glob.glob(os.path.join(path, "**/GCVI*.dat")) if timeselect(f,f[-17:-11],'%y%m%d',starttime,endtime,timefmt)]
    ###G_flist = glob2.glob(path+'**/GCVI*.dat')
    ###G_flist.sort()

    C_flist = [f for f in glob.glob(os.path.join(path, "**/CVI*.dat")) if timeselect(f,f[-17:-11],'%y%m%d',starttime,endtime,timefmt)]
    ###C_flist = glob2.glob(path+'**/CVI*.dat')
    ###C_flist.sort()
    
    CSD_flist = [f for f in glob.glob(os.path.join(path_CVISD, "*.txt")) if timeselect(f,f[-12:-6],'%y%m%d',starttime,endtime,timefmt)]

    # Define headers for the different files
    GCVI_head = ['date', 'time', 'visiblty', 'cloudstt', 'precstat',
                 'airspeed', 'humidity', 'temperat', 'covertmp', 'coverpwr',
                 'uppertmp', 'upperpwr', 'lowertmp', 'lowerpwr', 'vis_xmit',
                 'vis_recv', 'cvi_stat', 'compstat', 'vac_stat', 'blwrstat',
                 'blwr_pwr', 'de_icing', 'windtunl', 'airspdsp', 'covertsp',
                 'uppertsp', 'lowertsp', 'rhthresh', 'precsens', 'ignrprec',
                 'visthrsh', 'err_rprt', 'savedata']

    CVI_head = ['date', 'time', 'cnt_flow', 'cntflprs', 'cntfltmp', 'cnthtpwr',
                'instflow', 'tosmflow', 'lfe_flow', 'lfe_temp', 'cut_size',
                'airspeed', 'oat_temp', 'add_flow', 'addflwsp', 'addflwtm',
                'addflwpr', 'xs_flow', 'xsflowsp', 'xsflowtm', 'xsflowpr',
                'conetemp', 'cone_pwr', 'pylontmp', 'pylonpwr', 'sensrtmp',
                'sensrpwr', 'cntflwsp', 'cnttmpsp', 'tosmflsp', 'conetmsp',
                'pylntmsp', 'err_rprt', 'airspsrc', 'oatmpsrc', 'flwcntrl',
                'htrcntrl', 'de_icing', 'manl_mfc', 'savedata']
    
    CVISD_head = ['date', 'time', 'cnt_flow', 'cntflprs', 'cntfltmp', 'cnthtpwr',
                'instflow', 'tosmflow', 'lfe_flow', 'lfe_temp', 'cut_size',
                'airspeed', 'oat_temp', 'add_flow', 'addflwsp', 'addflwtm',
                'addflwpr', 'xs_flow', 'xsflowsp', 'xsflowtm', 'xsflowpr',
                'conetemp', 'cone_pwr', 'pylontmp', 'pylonpwr', 'sensrtmp',
                'sensrpwr', 'cntflwsp', 'cnttmpsp', 'tosmflsp', 'conetmsp',
                'pylntmsp', 'err_rprt', 'airspsrc', 'oatmpsrc', 'flwcntrl',
                'htrcntrl', 'de_icing', 'manl_mfc']


    # Initialise DataFrame lists
    GCVIdfs = []
    CVIdfs = []
    CVISDdfs = []

    #Choose which fields to output
    print('Choosing fields...')
    GCVI_wantedcols = ['date', 'time', 'visiblty', 'airspeed',
                       'cvi_stat', 'compstat', 'vac_stat', 'blwrstat',
                       'blwr_pwr', 'windtunl']
    CVI_wantedcols = ['date', 'time', 'cntfltmp', 'instflow', 'tosmflow', 'xs_flow', 'cut_size', 'airspeed']
    CVISD_wantedcols = ['date', 'time', 'instflow', 'tosmflow', 'xs_flow', 'cut_size', 'airspeed']

    # # Loop for reading the data files
    print('Reading data...')
    for file in range(len(G_flist)):
        # Read GCVI data
        GCVI_tmp = pd.read_csv(G_flist[file], sep='\t', skiprows=12,
                               header=None, names=GCVI_head, decimal='.') # CHANGED FROM , TO .
        # Append to list of GCVI dfs
        GCVIdfs.append(GCVI_tmp[GCVI_wantedcols])
        # Print which file was just read
        print(G_flist[file].split('/')[-1])

    for file in range(len(C_flist)): # ADDED THIS TO FIX DIFF. NO. OF FILES ISSUE
        # Read CVI data
        CVI_tmp = pd.read_csv(C_flist[file], sep='\t', skiprows=15,
                              header=None, names=CVI_head, decimal='.') # CHANGED FROM , TO .
        # Append to list of CVI dfs
        CVIdfs.append(CVI_tmp[CVI_wantedcols])
        # Print which file was just read
        print(C_flist[file].split('/')[-1])

    for file in range(len(CSD_flist)): # ADDED THIS TO FIX DIFF. NO. OF FILES ISSUE
        # Read CVISD data
        CVISD_tmp = pd.read_csv(CSD_flist[file], sep='\t| \t|  \t', skiprows=11,
                              header=None, index_col=False,names=CVISD_head, decimal='.') # CHANGED FROM , TO .
        # Append to list of CVISD dfs
        CVISDdfs.append(CVISD_tmp[CVISD_wantedcols])
        # Print which file was just read
        print(CSD_flist[file].split('/')[-1])
    
        
    # Delete the temporary files
    del GCVI_tmp
    del CVI_tmp
    if CSD_flist!=[]:
        del CVISD_tmp

    # Concatenate the df lists to single dfs
    print('Concatenating DataFrames...')
    GCVI = pd.concat(GCVIdfs)
    CVI = pd.concat(CVIdfs)
    if CSD_flist!=[]:
        CVISD = pd.concat(CVISDdfs)
        

    # # Make the final output DataFrames
    # Replace On/Off with 1/0
    print('Replacing On/Off strings with 1/0...')
    repdict = {'On': 1., 'Off': 0.}
    repdict2 = {'Yes': 1, 'No': 0}
    GCVI['cvi_stat'] = GCVI['cvi_stat'].map(repdict)
    GCVI['compstat'] = GCVI['compstat'].map(repdict)
    GCVI['vac_stat'] = GCVI['vac_stat'].map(repdict)
    GCVI['blwrstat'] = GCVI['blwrstat'].map(repdict)
    GCVI.reset_index(inplace=True, drop=True)


    # Make the status sum
    print('Calculating status sum...')
    GCVI = GCVI.assign(sum_stat=GCVI.cvi_stat + GCVI.compstat +\
                       GCVI.vac_stat + GCVI.blwrstat)

    # Make sure shit is numeric
    CVI.tosmflow = pd.to_numeric(CVI.tosmflow)
    CVI.cut_size = pd.to_numeric(CVI.cut_size)
    CVI.airspeed = pd.to_numeric(CVI.airspeed)
    if CSD_flist!=[]:
        CVISD.tosmflow = pd.to_numeric(CVISD.tosmflow)
        CVISD.cut_size = pd.to_numeric(CVISD.cut_size)
        CVISD.airspeed = pd.to_numeric(CVISD.airspeed)
    GCVI.airspeed = pd.to_numeric(GCVI.airspeed)
    GCVI.visiblty = pd.to_numeric(GCVI.visiblty)

    # Put together date & time columns as 'time' and drop 'date' !! changed it so that it now is done before EF calculation
    print('Combining date and time...')
    GCVI.time = pd.to_datetime(GCVI.date.values+' '+GCVI.time.values,
                               format='%y/%m/%d %H:%M:%S')
    GCVI.drop('date', axis=1, inplace=True)

    CVI.time = pd.to_datetime(CVI.date.values+' '+CVI.time.values,
                              format='%y/%m/%d %H:%M:%S')
    CVI.drop('date', axis=1, inplace=True)

    if CSD_flist!=[]:
        CVISD.time = pd.to_datetime(CVISD.date+' '+CVISD.time,
                              format='%y/%m/%d %H:%M:%S')
        CVISD.drop('date', axis=1, inplace=True)

    # Set time as index
    GCVI.set_index('time', inplace=True)
    CVI.set_index('time', inplace=True)
    if CSD_flist!=[]:
        CVISD.set_index('time', inplace=True)
    
    # Calculate enrichment factor
    print('Calculating enrichment factor...')
    CVI = CVI.assign(EF=CVI.airspeed * 1.67e-5 * 60 / (CVI.tosmflow * 0.001))
    #CVI = CVI.assign(EF_blwr=GCVI.loc[CVI.index, 'blwr_pwr'] * 0.614 * 1.67e-5 * 60 / (CVI.tosmflow * 0.001)) #before: CVI.assign(EF_blwr=GCVI.loc[CVI.index, 'blwr_pwr']...
    EF_mix = CVI.EF.copy()
    #EF_mix[GCVI.windtunl == 'Man'] = CVI.EF_blwr[GCVI.windtunl == 'Man']
    #CVI = CVI.assign(EF_mix=EF_mix)
    
    if CSD_flist!=[]:
        CVISD = CVISD.assign(EFSD=CVISD.airspeed * 1.67e-5 * 60 / (CVISD.tosmflow * 0.001))
    #CVISD = CVISD.assign(EFSD_blwr=GCVI.loc[CVISD.index, 'blwr_pwr'] * 0.614 * 1.67e-5 * 60 / (CVISD.tosmflow * 0.001)) #before: CVI.assign(EF_blwr=GCVI.loc[CVI.index, 'blwr_pwr']...
    if CSD_flist!=[]:
        EFSD_mix = CVISD.EFSD.copy()
    #EFSD_mix[GCVI.windtunl == 'Man'] = CVISD.EFSD_blwr[GCVI.windtunl == 'Man']
    #CVISD = CVISD.assign(EFSD_mix=EFSD_mix)
    
    GCVI['sum_stat_ext']=np.where((GCVI['windtunl']=='Automatc') & (GCVI['sum_stat']>0) & (GCVI['sum_stat']<4),2,np.nan) ## as a definition for 'switching' (not completely on or off)
    
    print('Finished data processing')
    
    GCVI=GCVI.loc[starttime:endtime]
    CVI=CVI.loc[starttime:endtime]
    if CSD_flist!=[]:
        CVISD=CVISD.loc[starttime:endtime]
    else:
        CVISD=pd.DataFrame()

    return GCVI, CVI, CVISD

# -----------------------------------------------------------------------------

# Function for reading UCPC data
def readUCPC(path=None, flist=None):
    ''' Function to read UCPC data

    Takes either the argument path = path to data folder as a string
    or flist = a list of paths for chosen data files as strings

    Returns a pandas DataFrame (or Series?)
    '''

    # Check if a path is given, else look for file list
    if path is not None:
        flist = glob2.glob(path+'*UCPC*.scn')
        flist.sort()
    elif flist is not None:
        flist.sort()
    else:
        print('You need to provide a path or a list of files...')

    # Empty list to fill with dfs
    UCPC = []

    for i, file in enumerate(flist):
	# Read file
        data = pd.read_csv(file, header=None, sep=',\t')

	# Make timestamp from first two columns
        timestamp = pd.to_datetime(data[0] + ' ' + data[1])

	# Pick out the data and put the timestamp as the index
        ucpc = pd.DataFrame(index=timestamp, data=data.iloc[:, 2].values)

	# Append dataframe to list
        UCPC.append(ucpc)

    # Concatenate dfs
    UCPC = pd.concat(UCPC)

    return UCPC

# -----------------------------------------------------------------------------

# Function for reading Mini-CWS data
def readMiniCWS(path=None, flist=None):
    ''' Function for reading Mini-CWS data

    Takes either the argument path = path to data folder as a string
    or flist = a list of paths for chosen data files as strings

    Returns a pandas DataFrame
    '''
    # Check if a path is given, else look for file list
    if path is not None:
        flist = glob2.glob(path+'*.csv')
        flist.sort()
    elif flist is not None:
        flist.sort()
    else:
        print('You need to provide a path or a list of files...')

    # Empty list to fill with dfs
    MiniCWS = []

    for i, file in enumerate(flist):
	# Read file
        df = pd.read_csv(file)

	# Make datetime index and drop those columns
        df.index = pd.to_datetime(df['System date'] + ' ' + df['GPS timestamp'])
        df.drop(['System date', 'GPS timestamp'], axis=1, inplace=True)

	# Append df to list
        MiniCWS.append(df)

    # Concatenate dfs
    MiniCWS =  pd.concat(MiniCWS)

    return MiniCWS

# -----------------------------------------------------------------------------

# Function for reading PVM data
def readPVM(path=None,starttime=None,endtime=None,timefmt=None):
    ''' Function for reading PVM data

    Takes path, starttime, endtime, and timefmt as strings

    Returns a pandas DataFrame
    '''
    # Check if a path is given, else look for file list
    
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime and timefmt as input needed...')

    flist = [f for f in glob2.glob(path+'*PVM*.txt') if timeselect(f,f[-12:-4],'%Y%m%d',starttime,endtime,timefmt)]

    # Empty list to fill with dfs
    PVM = []

    for i, file in enumerate(flist):
	# Read file
        df = pd.read_csv(file, sep='\t', parse_dates={'time': [0, 1, 2, 3, 4, 5]})

	# Make datetime index and drop time column
        df.index = pd.to_datetime(df['time'], format='%Y %m %d %H %M %S')
        df.drop('time', axis=1, inplace=True)

	# Append df to list
        PVM.append(df)

    # Concatenate dfs
    PVM = pd.concat(PVM)

    return PVM


# Read DMPS Finland data
def readDMPSFin(path=None,starttime=None,endtime=None,timefmt=None,filetype=None):
    ''' Function to read Finnish DMPS FAIRARI data

    Takes either the argument path = path to data folder as a string
    or flist = a list of paths for chosen data files as strings

    Returns a dictionary with fields: ...
    '''
    
    # check if all input is given
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime and timefmt as input needed...')

    flist = [f for f in glob.glob(path + "/inv_sd_neg*.csv") if timeselect(f,f[-12:-4],'%Y%m%d',starttime,endtime,timefmt)]
    #print(flist)
    
    
    #### read data and save to dataframe Data, 
    Dpmin_Fin=1.3 # random assumption
    li = []
    for filename in flist:
        #print(filename)
        df = pd.read_csv(filename,na_values='NaN')
        df.columns=df.columns.str[:15] # as sometimes the last digits of the diameter are slightly different
        dlogDp_Fin=np.log10(df.columns[1:].astype(float).values*10**(-9))-shift(np.log10(df.columns[1:].astype(float).values*10**(-9)),1,cval=np.nan)
        dlogDp_Fin[0]=np.log10(df.columns[1:].astype(float).values*10**(-9))[0]-np.log10(Dpmin_Fin*10**(-9))
        df.insert(0, 'Ntot_int', (dlogDp_Fin*df.iloc[:,1:]).sum(axis=1))
        df.insert(1, 'Ntot_cpc', np.nan)
        li.append(df)

    Data = pd.concat(li, axis=0, ignore_index=True)
    Data.index=pd.to_datetime(Data['Time'], format='%Y-%m-%d %H:%M:%S')
    Data.drop(['Time'], axis=1, inplace=True)


    Data=Data.loc[starttime:endtime]
    
    return Data



# -----------------------------------------------------------------------------

# Function for reading CCNC data
def readCCNC(path=None,starttime=None,endtime=None,timefmt=None):
    ''' Function for reading CCNC data

    Takes path, starttime, endtime, and timefmt as strings

    Returns a pandas DataFrame
    '''
    # check if all input is given
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime and timefmt as input needed...')

    files = [f for f in glob.glob(os.path.join(path, "*.csv")) if timeselect(f,f[-16:-10],'%y%m%d',starttime,endtime,timefmt)]
    
    # open files between start and end and concat them in DataFrame CCNC
    li = []
    
    for filename in files:
        df = pd.read_csv(filename, index_col=None, skiprows=2,header=1)
        df['Date']=filename[-16:-10]
        li.append(df)

    CCNC = pd.concat(li, axis=0, ignore_index=True)
    CCNC.columns = CCNC.columns.str.replace(' ', '')
    CCNC['datetime']=CCNC['Date'] + ' ' + CCNC['Time']
    CCNC.index=pd.to_datetime(CCNC['datetime'],format='%y%m%d %H:%M:%S')#-pd.Timedelta('1S')
    CCNC=CCNC.drop(columns=['datetime'])
    
    CCNC=CCNC.loc[starttime:endtime]
    
    return CCNC

# -----------------------------------------------------------------------------

# Function for quality checking CCNC data
def qualCCNC(Data=None,SSexclude=0,SSexclude_long=0,Concmax=None):
    ''' Function for quality checking CCNC data

    Takes pandas DataFrame and how many datasteps to exclude 
    after change in supersaturation (SSexclude) 
    and after change from highest to lowest SS (SSexclude_long);
    
    Check if: 
    Binsizes have been changed from defaults,
    Temperature is stabilized (SS),
    

    Returns a pandas DataFrame
    '''
    
    if Data is None:
        print('You need to provide a pandas DataFrame...')
    
    # Bin sizes. If lower limit is not 0, print error message
    if Data['Bin#'].any()>0:
        raise SystemExit('STOP: array with bin limits has to be changed!!')
    Bin_up=[0.75,1.0,1.5,2.0,2.5,3.0,3.5,4.0,4.5,5.0,5.5,6.0,6.5,7.0,7.5,8.0,8.5,9.0,9.5,10]#\mu m
   ### exclude where CurrentSS is not the targeted SS, based on number of occurence (at least 10% of max occurence)
    # e.g. SS=[0.006,0.2,0.4,0.6,0.60123,0.8] becomes [0.2,0.4,0.6,0.8]
    Data=Data.mask(Data['CurrentSS'].isin(Data.groupby(['CurrentSS']).count()[Data.groupby(['CurrentSS']).count().Time<0.1*Data.groupby(['CurrentSS']).count().Time.max()].index))
 
    ### cumulated sum of how long current SS is lasting -> Data['SScount']
    Data=Data.assign(SScount=Data.groupby(Data.CurrentSS.ne(Data.CurrentSS.shift()).cumsum()).cumcount().add(1))
    
    ####### Quality check #########
    def num_after_point(x):
        s = str(x)
        if not '.' in s:
            return 0
        return len(s) - s.index('.') - 1

    SSdigits=[]
    for i in range(len(Data.groupby(['CurrentSS']).count().index)):
        comma=num_after_point(Data.groupby(['CurrentSS']).count().index[i])
        SSdigits.append(comma)
    
        
    ### Set first SSexclude timesteps after change in SS and timesteps with alarms to np.nan
    Data=Data.mask((Data['TempsStabilized']!=1)|
                   (Data['CCNNumberConc']>Concmax)|
                   (Data['SScount'] <= SSexclude)|
                   (Data['AlarmCode'] > 0))
                   #((Data['CurrentSS'] == Data.groupby(['CurrentSS']).count().idxmax()[0]) & (Data['SScount'] <= SSexclude_long)) )    
    
    ### For min. SS exclude a longer time as it takes longer for the CCNC to adapt
    Data=Data.mask((Data['CurrentSS'] == Data.groupby(['CurrentSS']).count().index[np.argmin(SSdigits)]) & (Data['SScount'] <= SSexclude_long)) 
    return Data

# -----------------------------------------------------------------------------

# Function for reading RH/T data
def readRHT(path=None,starttime=None,endtime=None,timefmt=None):
    ''' Function for reading RH/T sensor data

    Takes either the argument path = path to data folder as a string
    or flist = a list of paths for chosen data files as strings

    Returns a pandas DataFrame
    '''
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime and timefmt as input needed...')

    files = [f for f in glob.glob(os.path.join(path, "*.csv")) if timeselect(f,f[-20:-12],'%y-%m-%d',starttime,endtime,timefmt)]
    
    
    # Empty list to fill with dfs
    RHT = []

    for i, file in enumerate(files):
	# Read file
        df = pd.read_csv(file, skiprows=3, names=['number', 'date', 'time', 'Ta', 'RH', 'P', 'Tdf','none'])
        
	# Make datetime index and drop those columns (plus the weird empty column)
        df.index = pd.to_datetime(df['date'] + ' ' + df['time'], format='%d.%m.%Y %H:%M:%S')
        df.drop(['date', 'time', 'none'], axis=1, inplace=True)

	# Append dfs to list
        RHT.append(df)

    # Concatenate dfs
    RHT = pd.concat(RHT)
    
    RHT=RHT.loc[starttime:endtime]
    
    return RHT

# -----------------------------------------------------------------------------

# Function for reading Flow meter data
def readFlowM(path=None,starttime=None,endtime=None,timefmt=None):
    ''' Function for reading TSI flow meter data (added to DMPS-Rackham)

    Takes either the argument path = path to data folder as a string
    or flist = a list of paths for chosen data files as strings

    Returns a pandas DataFrame
    '''
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime and timefmt as input needed...')

    flist = [f for f in glob.glob(os.path.join(path, "*.scn")) if (f[-25:-15]=='MFC_TSI_01') and (timeselect(f,f[-14:-4],'%Y-%m-%d',starttime,endtime,timefmt))]
    
    # Empty list to fill with dfs
    Flow = []

    for i, file in enumerate(flist):
	# Read file
        df = pd.read_csv(file, skiprows=1, sep=',\t|\t',names=['date', 'time', 'Flow', 'T', 'P'])
        
	# Make datetime index and drop those columns (plus the weird empty column)
        df.index = pd.to_datetime(df['date'] + ' ' + df['time'], format='%Y-%m-%d %H:%M:%S')
        df.drop(['date', 'time'], axis=1, inplace=True)

	# Append dfs to list
        Flow.append(df)

    # Concatenate dfs
    Flow = pd.concat(Flow)
    
    Flow=Flow.loc[starttime:endtime]
    
    return Flow

# -----------------------------------------------------------------------------

# Function for reading Sonic data
def readSonic(path=None,starttime=None,endtime=None,timefmt=None):
    ''' Function for reading Sonic data

    Takes either the argument path = path to data folder as a string
    or flist = a list of paths for chosen data files as strings

    Returns a pandas DataFrame
    '''
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime and timefmt as input needed...')

    flist = [f for f in glob.glob(os.path.join(path, "*/*.dat")) if (timeselect(f,f[-12:-4],'%y%m%d%H',starttime,endtime,timefmt))]

    # Empty list to fill with dfs
    Sonic = []

    for i, file in enumerate(flist):
	# Read file
        print(file)
        df = pd.read_csv(file, sep=' |:|,',names=['time', 'UTC', 'heating', 'u', 'v','w','T_ac'])

        # Make datetime index and drop those columns (plus the weird empty column)
        df.index = pd.to_datetime(df['time'], format='%y%m%d%H%M%S')
        df.drop(['time','UTC'], axis=1, inplace=True)
        df=df.iloc[np.where(df['u']!='x')]
        df[df.columns[1:]] = df.iloc[:, 1:].astype('float')
        df_max=df.resample('1S').max()
        df_max.columns = [str(col) + '_max' for col in df_max.columns]
        df_min=df.resample('1S').min()
        df_min.columns = [str(col) + '_min' for col in df_min.columns]
        df=df.resample('1S').mean()
        df=pd.concat([df,df_min['w_min'],df_max['w_max']],axis=1)
        
	# Append dfs to list
        Sonic.append(df)

    # Concatenate dfs
    Sonic = pd.concat(Sonic)
    Sonic['v_h']=np.sqrt(np.abs(Sonic['u'])**2+np.abs(Sonic['v'])**2)
    Sonic=Sonic/100 # to get to standard units
    Sonic['v_dir']=np.mod(180+np.rad2deg(np.arctan2(Sonic['u'], Sonic['v'])),360)
    
    
    Sonic=Sonic.loc[starttime:endtime]
    print('M: heater off, H: heater on')
    
    return Sonic

# -----------------------------------------------------------------------------

# Function for reading Sonic data
def readSonicLR(path=None,starttime=None,endtime=None,timefmt=None):
    ''' Function for reading Sonic data

    Takes either the argument path = path to data folder as a string
    or flist = a list of paths for chosen data files as strings

    Returns a pandas DataFrame
    '''
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime and timefmt as input needed...')

    flist = [f for f in glob.glob(os.path.join(path, "*.raw")) if (timeselect(f,f[-14:-4],'%Y-%m-%d',starttime,endtime,timefmt))]

    # Empty list to fill with dfs
    Sonic = []

    for i, file in enumerate(flist):
	# Read file
        print(file)
        df = pd.read_csv(file, sep=' |:|,|\t',names=['date', 'H','M','S', 'heating', 'u', 'v','w','T_ac'])
        # Make datetime index and drop those columns (plus the weird empty column)
        df.index = pd.to_datetime(df['date']+' '+df['H'].astype(str)+':'+df['M'].astype(str)+':'+df['S'].astype(str), format='%Y-%m-%d %H:%M:%S')
        df.drop(['date','H','M','S'], axis=1, inplace=True)
        df=df.iloc[np.where(df['u']!='x')]
        df[df.columns[1:]] = df.iloc[:, 1:].astype('float')
        df_max=df.resample('1S').max()
        df_max.columns = [str(col) + '_max' for col in df_max.columns]
        df_min=df.resample('1S').min()
        df_min.columns = [str(col) + '_min' for col in df_min.columns]
        df=df.resample('1S').mean()
        df=pd.concat([df,df_min['w_min'],df_max['w_max']],axis=1)
        
	# Append dfs to list
        Sonic.append(df)

    # Concatenate dfs
    Sonic = pd.concat(Sonic)
    Sonic['v_h']=np.sqrt(np.abs(Sonic['u'])**2+np.abs(Sonic['v'])**2)
    Sonic=Sonic/100 # to get to standard units
    Sonic['v_dir']=np.mod(180+np.rad2deg(np.arctan2(Sonic['u'], Sonic['v'])),360)
    
    
    Sonic=Sonic.loc[starttime:endtime]
    print('M: heater off, H: heater on')
    
    return Sonic


# -----------------------------------------------------------------------------

# Function for reading MBS data
def readMBS(path=None, flist=None):
    ''' Function for reading MBS data

    Takes either the argument path = path to data folder as a string
    or flist = a list of paths for chosen data files as strings

    Returns a dictionary of pandas DataFrames
    '''
    if path is not None:
        # Get list of files in path directory
        flist = glob2.glob(path+'/*.csv')
        # Sort the files
        flist.sort()

    # Empty list to fill with dfs
    dflist = []

    # Loop over the list
    for i, file in enumerate(flist):
        print(file)
        # Read the actual data
        df = pd.read_csv(file, skiprows=33) # used to be 32! changed when warren added a thing

        # Get the start time from line 33 (index 32)
        fp = open(file)
        for i, line in enumerate(fp):
            if i == 32:
                starttime = pd.to_datetime(line[16:], dayfirst=True) # needed to add dayfirst
            elif i > 32:
                break
        fp.close()

        # Combine the start time and the milliseconds from the file and make a time index
        df['time'] = starttime + pd.to_timedelta(df['Time(ms)'], unit='ms')
        df.drop(['Time(ms)'], axis=1, inplace=True)
        df.set_index('time', inplace=True)

        # Append df to list
        dflist.append(df)

    # Concatenate dfs
    df = pd.concat(dflist)

    # CA1 covers the first 512 columns
    CA1 = df.iloc[:, :512]
    # CA2 the next 512
    CA2 = df.iloc[:, 512:1024]
    # Xenon channels
    XE = df.iloc[:, 1025:1033]
    # Some statistics about the fluorescence that are already calculated
    LRstats = df.iloc[:, 1039:]
    # The rest, which is more simple data that doesn't really belong in the other groups
    other = df.iloc[:, [1024, 1033, 1034, 1035, 1036, 1037, 1038]]

    MBS = {'CA1': CA1, 'CA2': CA2, 'XE': XE, 'LRstats': LRstats, 'other': other}

    return MBS

# -----------------------------------------------------------------------------

# Function for reading Swiss CPC data
def readSwissCPC(path=None, flist=None):
    ''' Function to read Swiss CPC data

    Takes either the argument path = path to data folder as a string
    or flist = a list of paths for chosen data files as strings

    Returns a pandas DataFrame (or Series?)
    '''

    # Check if a path is given, else look for file list
    if path is not None:
        flist = glob2.glob(path+'*CPC*.csv')
        flist.sort()
    elif flist is not None:
        flist.sort()
    else:
        print('You need to provide a path or a list of files...')

    CPC = []

    for i, file in enumerate(flist):
        data = pd.read_csv(file)

        data.index = pd.to_datetime(data['TimeEnd'], format='%d.%m.%y %H:%M:%S')

        data.drop('TimeEnd', axis=1, inplace=True)

        CPC.append(data)

    CPC = pd.concat(CPC)

    return CPC

# -----------------------------------------------------------------------------

# Function for reading WELAS data
def readWELAS(path=None, flist=None):
    ''' Function to read WELAS data

    Takes either the argument path = path to data folder as a string
    or flist = a list of paths for chosen data files as strings

    Returns a dictionary with two pandas DataFrames (size distr. and other)
    '''
    # Check if a path is given, else look for file list
    if path is not None:
        flist = glob2.glob(path+'*.scn')
        flist.sort()
    elif flist is not None:
        flist.sort()
    else:
        print('You need to provide a path or a list of files...')

    # Empty lists to fill with dfs
    sizeDistr = []
    otherStuff = []

    # Bin midpoint diameter in metres
    sizeDistr_header = np.array([0.148647, 0.159737, 0.171655, 0.184462,
                                 0.198224, 0.213013, 0.228905, 0.245984,
                                 0.264336, 0.284057, 0.305250, 0.328024,
                                 0.352497, 0.378797, 0.407058, 0.437427,
                                 0.470063, 0.505133, 0.542820, 0.583319,
                                 0.626839, 0.673606, 0.723862, 0.777868,
                                 0.835903, 0.898268, 0.965286, 1.037304,
                                 1.114695, 1.197860, 1.287230, 1.383267,
                                 1.486470, 1.597372, 1.716548, 1.844616,
                                 1.982239, 2.130130, 2.289054, 2.459835,
                                 2.643358, 2.840573, 3.052502, 3.280243,
                                 3.524975, 3.787966, 4.070578, 4.374274,
                                 4.700629, 5.051333, 5.428202, 5.833189,
                                 6.268390, 6.736061, 7.238624, 7.778682,
                                 8.359033, 8.982682, 9.652861]) * 1e-6

    # Header for the stuff that isn't the size distribution
    otherStuff_header = ['St.SensFlow[bit]', 'St.Coincid[bit]',
                         'St.SucPump[bit]', 'St.WhStation[bit]',
                         'St.iADS[bit]', 'St.RawChanDev[bit]',
                         'St.LEDTemp[bit]', 'St.OpModus[bit]',
                         'Param8[Unit]', 'Param9[Unit]', 'Param10[Unit]',
                         'Param11[Unit]', 'Param12[Unit]', 'Param13[Unit]',
                         'Param14[Unit]', 'Param15[Unit]', 'Param16[Unit]',
                         'Param17[Unit]', 'Param18[Unit]', 'Param19[]',
                         'Velocity[m/s]', 'Coincidense[%]', 'Modus[Unit]',
                         'SucPmpOutput[%]', 'iADSTempSens1[°C]',
                         'RawChanDev[channels]', 'LEDTemp[°C]',
                         'FlowRate[l/min]', 'Cn_UF-CPC[Unit]',
                         'x50DropDiam[µm]', 'CondUnitTemp[°C]',
                         'Temperature[°C]', 'RelHum[%]', 'WindSpeed[km/h]',
                         'WindDir[°]', 'PrecipIntens[l/m2/h]', 'PrecipType[?]',
                         'TempDewPoint[°C]', 'AirPressure[hPa]',
                         'WindSignQual[%]', 'Cn[P/cm3]', 'PM1[µg/m3]',
                         'PM2.5[µg/m3]', 'PM4[µg/m3]', 'PM10[µg/m3]',
                         'PMTotal[µg/m3]', 'EXTRA']


    for i, file in enumerate(flist):
        # Read file and set datetime index
        df = pd.read_csv(file, sep=',\t', skiprows=1, header=None,
                         parse_dates=[0])
        df.set_index(0, drop=True, inplace=True)

        # Pick out the size distribution and make the columns floats
        df_sizedist = df.iloc[:, 47:]
        df_sizedist.columns = pd.Float64Index(sizeDistr_header)

        # Pick out the other stuff and specify column names
        df_other = df.iloc[:, :47]
        df_other.columns = otherStuff_header

        # Append dfs to lists
        sizeDistr.append(df_sizedist)
        otherStuff.append(df_other)

    # Concatenate dfs
    sizeDistr = pd.concat(sizeDistr)
    otherStuff = pd.concat(otherStuff)

    WELAS = {'Size distribution': sizeDistr, 'Other stuff': otherStuff}

    return WELAS

# -----------------------------------------------------------------------------

# Function for reading APS data
def readAPS(path=None, flist=None):
    ''' Function to read APS data

    Takes either the argument path = path to data folder as a string
    or flist = a list of paths for chosen data files as strings

    Returns a dictionary with two pandas DataFrames (size distr. and other)
    '''
    # Check if a path is given, else look for file list
    if path is not None:
        flist = glob2.glob(path+'*APS*.txt')
        flist.sort()
    elif flist is not None:
        flist.sort()
    else:
        print('You need to provide a path or a list of files...')

    # Empty list to fill with dfs
    dfs = []

    for i, file in enumerate(flist):
	# Use this to work around stupid non-utf-8 symbol
        with open(file, 'r', encoding='utf8', errors='ignore') as f:
            df = pd.read_csv(f, skiprows=6)
        # Set datetime index and drop those columns
        df.index = pd.to_datetime(df['Date'] + ' ' + df['Start Time'],
                                  format='%m/%d/%y %H:%M:%S')
        df.drop(['Date', 'Start Time'], axis=1, inplace=True)

        # Fix the stupid non-utf-8 column
        df['Total Conc.'] = df['Total Conc.'].apply(lambda x: pd.to_numeric(x.split('(')[0])).values

        dfs.append(df)

    # Concatenate dfs
    dfs = pd.concat(dfs)
    # Pick out size distribution and make columns numeric
    sizeDistr = dfs.iloc[:, 3:54].apply(pd.to_numeric)
    sizeDistr.columns = pd.Float64Index(pd.to_numeric(sizeDistr.columns)*1e-6)
    # Pick out other stuff
    otherStuff = df.iloc[:, 54:]

    APS = {'Size distribution': sizeDistr, 'Other stuff': otherStuff}

    return APS

# -----------------------------------------------------------------------------

# Function for reading Leeds SMPS data
def readLeedsSMPS(path=None, flist=None):
    ''' Function to read Leeds SMPS data

    Takes either the argument path = path to data folder as a string
    or flist = a list of paths for chosen data files as strings

    Returns a dictionary with two pandas DataFrames (size distr. and other)
    '''
    # Check if a path is given, else look for file list
    if path is not None:
        flist = glob2.glob(path+'*.csv')
        flist.sort()
    elif flist is not None:
        flist.sort()
    else:
        print('You need to provide a path or a list of files...')

    # Empty list to fill with dfs
    dfs = []

    for i, file in enumerate(flist):
	# Use this to work around stupid non-utf-8 symbol
        with open(file, 'r', encoding='utf8', errors='ignore') as f:
            df = pd.read_csv(f, skiprows=6)
        # Set datetime index and drop those columns
        df.index = pd.to_datetime(df['Date'] + ' ' + df['Start Time'],
                                  format='%m/%d/%y %H:%M:%S')
        df.drop(['Date', 'Start Time'], axis=1, inplace=True)

        # Fix the stupid non-utf-8 column
        df['Total Conc.'] = df['Total Conc.'].apply(lambda x: pd.to_numeric(x.split('(')[0])).values

        dfs.append(df)

    # Concatenate dfs
    SMPS = pd.concat(dfs)

    return SMPS

# -----------------------------------------------------------------------------

# Function for trapezoidal integration ignoring NaNs
def nantrapz(row, above=0.0):
    ''' Function for trapezoidal integration ignoring NaNs

    To be applied row-wise to dataframes with size distributions
    that have the diameters (in metres) as column names.

    The keyword "above" can be used to specify that the integration
    should only be for particles above that size (NB: in nanometres!)

    Returns the integrated value for each row
    '''
    above = above * 1e-9
    y = row.loc[above:].copy()
    mask = np.isfinite(y)
    y = y[mask].copy()
    x = y.index.copy()

    r = np.trapz(y, x=np.log10(x))
    return r

# -----------------------------------------------------------------------------

# Function to match Nautilus and GCVI
def cloudloop(nautilus, GCVI, CVI):
    ''' Big ol' function including the CVI loop and everything.
    
    Arguments
            nautilus : the dictionary with Nautilus data that is the output of readDMPS
            GCVI, CVI : the outputs from the readGCVI function
        
    Returns a new Nautilus dictionary with cloud flags, plus a dictionary with CVI stuff (visibility etc)
    ''' 
    # # # # =========== SCAN LENGTH THING FOR DMPS ============= # # # #
    # Get times (midpoints of scans) and round to nearest second
    time = nautilus.index.copy().round('S') #nautilus['dNdlogD'].index.copy().round('S')
    # Calculate scan lengths
    scanTimes = (time[2:] - time[:-2]) / 2
    # Special for first and last scan since there's no other way of knowing
    scanTimes = scanTimes.insert(0, time[1] - time[0])
    scanTimes = scanTimes.insert(-1, time[-1] - time[-2])

    # Find indices where scan time is longer than 7 mins (i.e., something's up,
    # because the two predominant scan length settings are 00:07:00 and 00:06:24)
    idx = np.where(scanTimes > pd.Timedelta('20m'))[0] #np.where(scanTimes > pd.Timedelta('7m'))[0]

    # Make scanTimes into a numpy array so it's not immutable
    scanTimes = np.asanyarray(scanTimes)

    # Use alternative scan times for the points where it's too long
    # - the minimum of the scantime before and the scantime after
    for i in idx:
        try:
            scanTimes[i] = np.min((scanTimes[i-1], scanTimes[i+1]))
        except IndexError:
            try:
                scanTimes[i] = scanTimes[i-1]
            except IndexError:
                scanTimes[i] = scanTimes[i+1]
                
    # Round indices of dataframes to nearest second
    nautilus.index = nautilus.index.round('S') #nautilus['dNdlogD'].index = nautilus['dNdlogD'].index.round('S')
    #nautilus['Ntot_cpc'].index = nautilus['Ntot_cpc'].index.round('S')
    #nautilus['Ntot_int'].index = nautilus['Ntot_int'].index.round('S')

    # ------------------------------------------------------------------
    
    # # # # ============= MATCHY MATCHY LOOP =============== # # # #
    # dfs to fill
    # EF
    EF = pd.DataFrame(0, index=nautilus.index, columns=['EF', 'EF_flag', 'EF_blwr']) #nautilus['dNdlogD'].index
    # Cut-off size
    cloudCutSize = pd.DataFrame(0, index=nautilus.index, columns=['median', 'mean', 'std']) #nautilus['dNdlogD'].index
    # Visibility
    visibility = pd.DataFrame(0, index=nautilus.index, columns=['median', 'mean', 'std', 'min', 'max']) #nautilus['dNdlogD'].index
    # Cloud flag
    cloudFlag = pd.DataFrame(0, index=nautilus.index, columns=['cloud']) #nautilus['dNdlogD'].index

    # Calculate half scan lengths and 10 second timedelta to avoid in-loop calc.
    halfscans = scanTimes * 0.5
    tdelta = pd.Timedelta(seconds=10)

    # Do the loop
    for i, time in enumerate(nautilus.index):#nautilus['dNdlogD'].index
        print('Loop', i, 'of', len(nautilus.index)-1) #nautilus['dNdlogD'].index
        # Get start and stop times (plus minus 10 seconds to be safe)
        start = time - halfscans[i] - tdelta
        stop = time + halfscans[i] + tdelta

        # If the GCVI was recording, flag data and calculate stuff
        if len(GCVI.loc[start:stop]) > 0:
            # Calculate average visibility and its standard deviation
            visibility.loc[time, 'mean'] = np.mean(GCVI.loc[start:stop, 'visiblty'])
            visibility.loc[time, 'std'] = np.std(GCVI.loc[start:stop, 'visiblty'])
            visibility.loc[time, 'median'] = np.nanmedian(GCVI.loc[start:stop, 'visiblty'])
            visibility.loc[time, 'min'] = np.min(GCVI.loc[start:stop, 'visiblty'])
            visibility.loc[time, 'max'] = np.max(GCVI.loc[start:stop, 'visiblty'])

            # If the entire Nautilus scan was in-cloud
            if np.min(GCVI.loc[start:stop, 'sum_stat']) == 4:
                # Set cloud flag to yes
                cloudFlag.loc[time, 'cloud'] = 'yes'

                # Calculate median enrichment factor for the scan
                EF.loc[time, 'EF'] = np.nanmean(CVI.loc[start:stop, 'airspeed']) * 1.67e-5 \
                                     * 60 / (np.nanmean(CVI.loc[start:stop, 'tosmflow']) * 0.001)
                EF.loc[time, 'EF_blwr'] = np.nanmean(GCVI.loc[start:stop, 'blwr_pwr']) * 0.614 \
                                     * 1.67e-5 * 60 / (np.nanmean(CVI.loc[start:stop, 'tosmflow']) * 0.001)

                # Calculate average droplet cut-off size and standard deviation
                cloudCutSize.loc[time, 'mean'] = np.mean(CVI.loc[start:stop, 'cut_size'])
                cloudCutSize.loc[time, 'std'] = np.std(CVI.loc[start:stop, 'cut_size'])
                cloudCutSize.loc[time, 'median'] = np.nanmedian(CVI.loc[start:stop, 'cut_size'])

                # If CVI was not recording...
                if len(CVI.loc[start:stop]) < 1:
                    # Overwrite the enrichment factor with 6.5 for now
                    EF.loc[time, 'EF'] = 6.5
                    EF.loc[time, 'EF_flag'] = 1
            # If the entire Nautilus scan was NOT in-cloud
            #elif np.max(GCVI.loc[start:stop, 'sum_stat']) == 0:
            elif ((np.max(GCVI.loc[start:stop, 'sum_stat']) == 1) & (np.min(GCVI.loc[start:stop, 'cvi_stat']) == 1)) | (np.max(GCVI.loc[start:stop, 'sum_stat'] == 0)):
                # Set cloud flag to no
                cloudFlag.loc[time, 'cloud'] = 'no'
                # Set EF to 1 and EF_flag to 0
                EF.loc[time, 'EF'] = 1
                EF.loc[time, 'EF_flag'] = 0
                EF.loc[time, 'EF_mix'] = 1
                EF.loc[time, 'EF_blwr'] = 1
            # Else, it was switching...
            else:
                # Set cloud flag to switching
                cloudFlag.loc[time, 'cloud'] = 'switching'
        elif len(GCVI.loc[start:stop]) == 0:
            # If there is no GCVI data for a particular Nautilus time, drop it
            try:
                EF.drop(time, inplace=True)
                cloudCutSize.drop(time, inplace=True)
                visibility.drop(time, inplace=True)
                cloudFlag.drop(time, inplace=True)
            except:
                EF.loc[start:stop, :] = np.nan
                cloudCutSize.loc[start:stop, :] = np.nan
                visibility.loc[start:stop, :] = np.nan
                cloudFlag.loc[start:stop] = 'nan'

    CVIstuff = {'Enrichment factor': EF, 'Cut size': cloudCutSize, 'Visibility': visibility,
                'Cloud flag': cloudFlag}
    
    # # # # ========== ACTUALLY ADJUST NAUTILUS ======== # # # #
    # Adjust Nautilus based on EF and flag for clouds etc
    # Pick out the times that were actually in the GCVI
    dNdlogD = nautilus.iloc[:,2:].loc[cloudFlag.index, :] #nautilus['dNdlogD']
    Ntot_int = nautilus.loc[cloudFlag.index, 'Ntot_int']
    Ntot_cpc = nautilus.loc[cloudFlag.index, 'Ntot_cpc']

    # ----- Regular EF -----

    # Divide it by the enrichment factor
    dNdlogD = dNdlogD.div(EF.EF, axis=0)
    Ntot_int = Ntot_int.div(EF.EF, axis=0)
    Ntot_cpc = Ntot_cpc.div(EF.EF, axis=0)
    # Add cloud and EF flags
    dNdlogD['cloud'] = cloudFlag['cloud']
    dNdlogD['EF_flag'] = EF.EF_flag
    Ntot_int['cloud'] = cloudFlag['cloud']
    Ntot_int['EF_flag'] = EF.EF_flag
    Ntot_cpc['cloud'] = cloudFlag['cloud']
    Ntot_cpc['EF_flag'] = EF.EF_flag

    # Drop rows with NaNs/infs
    #dNdlogD = dNdlogD[Ntot_int[0].notnull()]#dNdlogD[Ntot_int[0].notnull()]
    Ntot_int.dropna(how='any', axis=0, inplace=True)
    Ntot_cpc.dropna(how='any', axis=0, inplace=True)
   
    nautilus_EF=dNdlogD
    nautilus_EF['Ntot_int']=Ntot_int
    nautilus_EF['Ntot_cpc']=Ntot_cpc
    nautilus_EF['cloud']=dNdlogD['cloud']
    nautilus_EF['EF_flag']=dNdlogD['EF_flag']

    #nautilus_EF = {'dNdlogD': dNdlogD, 'Ntot_int': Ntot_int, 'Ntot_cpc': Ntot_cpc}
    
    return nautilus_EF, CVIstuff

# -----------------------------------------------------------------------------

def readMAAP(path=None,starttime=None,endtime=None,timefmt=None):
    ''' Function for reading MAAP data

    Input path, starttime, endtime, and timefmt as strings

    Returns a pandas DataFrame with the chosen fields (see code)
    '''    
# check if all input is given
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime and timefmt as input needed...')

    flist = [f for f in glob.glob(os.path.join(path, "MAAP*.txt")) if timeselect(f,f[-14:-4],'%Y-%m-%d',starttime,endtime,timefmt)]
    
    
    # Define file header
    head = ['date', 'time', 'date_instr', 'time_instr', 'status', 'bc_conc',
            'bc_mass','airflow','a','b','c','d']

    # Initialise DataFrame list
    dfs = []

    # # Loop for reading the data files
    #print('Reading data...')
    for file in range(len(flist)):
        # Read data file
        df = pd.read_csv(flist[file], sep='\s+', header=None, names=head,
                         dtype={'status': object})

        # Drops rows that don't have all the fields (last value is NaN)
        df = df[~df.iloc[:, -1].isnull()]

        # Append to list of dfs
        dfs.append(df)

        # Print name of data file
        #print(flist[file].split('/')[-1])

    # Concatenate the df list to single df
    #print('Concatenating DataFrames...')
    MAAP = pd.concat(dfs)

    # Put together date & time columns as 'time' and drop 'date'
    #print('Combining date and time...')
    MAAP.time = pd.to_datetime(MAAP.date+' '+MAAP.time, format='%Y-%m-%d %H:%M:%S')
    MAAP.drop('date', axis=1, inplace=True)

    MAAP.time_instr = pd.to_datetime(MAAP.date_instr+' '+MAAP.time_instr,
                                     format='%y-%m-%d %H:%M:%S')
    MAAP.drop('date_instr', axis=1, inplace=True)

    MAAPout = MAAP.loc[:, ['time', 'time_instr', 'status', 'bc_conc', 'bc_mass','airflow','a','b','c','d']]
    MAAPout = MAAPout.reset_index(drop=True)
    MAAPout.set_index('time', inplace=True)
    MAAPout.index.names = ['datetime']

    MAAPout=MAAPout.loc[starttime:endtime]
    
    return MAAPout

# -----------------------------------------------------------------------------

# Function for reading FSSP data
def readFSSP(path=None, flist=None):
    # Check if a path is given, else look for file list
    if path is not None:
        flist = glob2.glob(path+'*.scn')
        flist.sort()
    elif flist is not None:
        flist = flist
        flist.sort()
    else:
        print('You need to provide a path or a list of files...')
      
    # Empty lists to fill with dfs
    R0_list = []
    R1_list = []
    R2_list = []
    R3_list = []

    # Bins for different FSSP ranges
    R0_bins = [3.5, 6.5, 9.5,12.5, 15.5, 18.5, 21.5, 24.5,
               27.5, 30.5, 33.5, 36.5, 39.5, 42.5, 45.5]
    R1_bins = [3.0, 5.0, 7.0, 9.0, 11.0, 13.0, 15.0, 17.0,
               19.0, 21.0, 23.0, 25.0, 27.0, 29, 31]
    R2_bins = [1.5, 2.5, 3.5, 4.5,  5.5,  6.5,  7.5,  8.5, 
               9.5, 10.5, 11.5, 12.5, 13.5, 14.5, 15.5]
    R3_bins = [0.75, 1.25, 1.75, 2.25, 2.75, 3.25, 3.75, 4.25,
               4.75, 5.25, 5.75, 6.25, 6.75, 7.25, 7.75]

    
    for i, file in enumerate(flist):
        # Read file
        df = pd.read_csv(file, header=None)

        # Make index: every fifth row, starting from 0
        index = pd.to_datetime(df.iloc[0::5, 0])

        # Make dfs for each range
        # Range 0: every fifth row, starting from 1
        R0 = df.iloc[1::5, 0].str.split('\t', expand=True)
        R0 = R0.drop([0, 16], axis=1).apply(pd.to_numeric)
        R0.index = index
        R0.columns = R0_bins

        # Range 1: every fifth row, starting from 2
        R1 = df.iloc[2::5, 0].str.split('\t', expand=True)
        R1 = R1.drop([0, 16], axis=1).apply(pd.to_numeric)
        R1.index = index
        R1.columns = R1_bins

        # Range 2: every fifth row, starting from 3
        R2 = df.iloc[3::5, 0].str.split('\t', expand=True)
        R2 = R2.drop([0, 16], axis=1).apply(pd.to_numeric)
        R2.index = index
        R2.columns = R2_bins

        # Range 3: every fifth row, starting from 4
        R3 = df.iloc[4::5, 0].str.split('\t', expand=True)
        R3 = R3.drop([0, 16], axis=1).apply(pd.to_numeric)
        R3.index = index
        R3.columns = R3_bins
        
        # Append dfs to lists
        R0_list.append(R0)
        R1_list.append(R1)
        R2_list.append(R2)
        R3_list.append(R3)
       
    # Concatenate dataframes 
    R0 = pd.concat(R0_list)
    R1 = pd.concat(R1_list)
    R2 = pd.concat(R2_list)
    R3 = pd.concat(R3_list)
    
    FSSP = {'Range 0': R0, 'Range 1': R1, 'Range 2': R2, 'Range 3': R3}
    
    return FSSP

# -----------------------------------------------------------------------------

# Function for reading .had file
def readHADFILE(path=None, flist=None):
    ''' Function to read .had file

    Takes either the argument path = path to data folder as a string
    or flist = a list of paths for chosen data files as strings

    Returns a pandas DataFrame
    '''

    # Check if a path is given, else look for file list
    if path is not None:
        flist = glob2.glob(path+'*.had')
        flist.sort()
    elif flist is not None:
        flist.sort()
    else:
        print('You need to provide a path or a list of files...')

    had = []

    for i, file in enumerate(flist):
        data = pd.read_csv(file, sep='\t', parse_dates={'time': [0, 1]})

        data.set_index('time', drop=True, inplace=True)

        had.append(data)

    had = pd.concat(had)

    return had

# -----------------------------------------------------------------------------

# Function for reading .scn file
def readSCNFILE(path=None, flist=None,starttime=None,endtime=None,timefmt=None,identifier='01'):
    ''' Function to read .scn file

    Takes either the argument path = path to data folder as a string
    or flist = a list of paths for chosen data files as strings

    Returns a pandas DataFrame
    '''
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime and timefmt as input needed...')

    flist = [f for f in glob2.glob(path+'/*CPC*_'+identifier+'-*.scn') if timeselect(f,f[-14:-4],'%Y-%m-%d',starttime,endtime,timefmt)]
    
    
    
    # Check if a path is given, else look for file list
    #if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
    #    print('path, starttime, endtime and timefmt as input needed...')
    #    flist = glob2.glob(path+'*CPC*_'+identifier+'-*.scn')
    #    flist.sort()
    #elif flist is not None:
    #    flist.sort()
    #else:
    #    print('You need to provide a path or a list of files...')

    scn = []

    header = ['Date','Time','Concent[cm^-3]', 'Rawconc[cm^-3]', 'Cnt_sec[sec^-1]',
              'Condtmp[C]', 'Satttmp[C]', 'Satbtmp[C]', 'Optctmp[C]',
              'Inlttmp[C]', 'Smpflow[cc/min]', 'Satflow[cc/min]', 'Pressur[mbar]',
              'Condpwr[level]', 'Sattpwr[level]', 'Satbpwr[level]', 'Optcpwr[level]',
              'Satfpwr[level]', 'Fillcnt[count]', 'Err_num[code]']

    for i, file in enumerate(flist):
        data = pd.read_csv(file, skiprows=1, header=None, names=header, sep=',\t|\t|,')
        if identifier=='01':
            data.index = pd.to_datetime(data.loc[:,'Date']+' '+data.loc[:,'Time'], format='%Y-%m-%d %H:%M:%S')
        elif identifier=='02':
            data.index = pd.to_datetime(data.loc[:,'Date']+' '+data.loc[:,'Time'], format='%Y-%m-%d %H:%M:%S')
        else:
            print('check identifier')
        data.drop(['Date','Time'], axis=1, inplace=True)
        data = data.apply(pd.to_numeric)

        scn.append(data)

    scn = pd.concat(scn)
    
    scn=scn.loc[starttime:endtime]
    
    return scn


# Read Rackham stp data
def readstp(path=None,starttime=None,endtime=None,timefmt=None,filetype=None):
    ''' Function to read Rackham stp data

    Takes either the argument path = path to data folder as a string
    or flist = a list of paths for chosen data files as strings

    Returns a dictionary with fields: ...
    '''
    
    # check if all input is given
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime and timefmt as input needed...')

    flist = [f for f in glob.glob(path + "*.stp") if timeselect(f,f[-14:-4],'%Y-%m-%d',starttime,endtime,timefmt)]
    
    #### read data and save to dataframe Data, 
    li = []
    for filename in flist:
        df = pd.read_csv(filename,sep=',\t|\t,', index_col=None, skiprows=0,header=0)
        li.append(df)

    Data = pd.concat(li, axis=0, ignore_index=True)
    Data.index=pd.to_datetime(Data['Date']+' '+Data['Time'],format='%Y-%m-%d %H:%M:%S',errors='coerce')
    Data.drop(['Date', 'Time'], axis=1, inplace=True)
    Data=Data.loc[starttime:endtime]
    
    return Data


# -----------------------------------------------------------------------------

# Read ship data
def readShipdata(path=None, flist=None):
    # Check if a path is given, else look for file list
    if path is not None:
        flist = glob2.glob(path+'ship*us.csv')
        flist.sort()
    elif flist is not None:
        flist.sort()
    else:
        print('You need to provide a path or a list of files...')

    # Empty list to fill with dfs
    dfs = []

    for i, file in enumerate(flist):
        df = pd.read_csv(file, parse_dates=[0])
        df.set_index('Timestamp', drop=True, inplace=True)

        dfs.append(df)

    # Concatenate dfs
    ship = pd.concat(dfs)

    return ship



# -----------------------------------------------------------------------------

# Read GFAS data
def readoldGFAS(path=None,starttime=None,endtime=None,timefmt=None,filetype=None):
    ''' Function to read GFAS data

    Takes either the argument path = path to data folder as a string
    or flist = a list of paths for chosen data files as strings

    Returns a dictionary with fields: ...
    '''

    # check if all input is given
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime and timefmt as input needed...')

    if filetype=='GFAS_User_Data*.zip':
        flist = [f for f in glob.glob(os.path.join(path, "*/*/", filetype)) if timeselect(f,f[-62:-54],'%Y%m%d',starttime,endtime,timefmt)]
    elif filetype=='GFAS_Diagnostic_Data*.zip':
        flist = [f for f in glob.glob(os.path.join(path, "*/*/", filetype)) if timeselect(f,f[-68:-60],'%Y%m%d',starttime,endtime,timefmt)]
    else:
        print('something wrong with name of filetype')
        
    dfs=[]
    for file in range(len(flist)):
        try:
            # Read data file
            df = pd.read_csv(flist[file],delimiter=',',compression='zip',usecols=np.linspace(0,83,84).astype(int))
            df.rename(columns = lambda x: x[0:6] if x.startswith('Bin') else x,inplace=True)
            df.rename(columns = lambda x: x[0:-1] if x.endswith(' ') else x,inplace=True)
            df.set_index('Time Stamp (UTC sec)', inplace=True)
            df['datetime']=pd.to_datetime(dt.datetime(1904,1,1)) + pd.to_timedelta(df.index.values,'s')
            df.set_index('datetime', inplace=True)
            dfs.append(df)
        except EmptyDataError:
            print(f"Zipping was not working for {flist[file]}")
#            try:
#                newfile=flist[file][:-4]+'.csv'
#                df = pd.read_csv(newfile,delimiter=',',usecols=np.linspace(0,83,84).astype(int))
#                df.rename(columns = lambda x: x[0:6] if x.startswith('Bin') else x,inplace=True)
#                df.rename(columns = lambda x: x[0:-1] if x.endswith(' ') else x,inplace=True)
#                df.set_index('Time Stamp (UTC sec)', inplace=True)
#                df['datetime']=pd.to_datetime(dt.datetime(1904,1,1)) + pd.to_timedelta(df.index.values,'s')
#                df.set_index('datetime', inplace=True)
#                dfs.append(df)
#            except:
#                continue
            continue
    
    GFAS = pd.concat(dfs)
    GFAS=GFAS.loc[starttime:endtime]
    if filetype=='GFAS_User_Data*.zip':
        bins=np.array([0.5,0.55,0.6,0.65,0.7,0.75,0.8,0.85,0.9,0.95,1,2.65,3.1,5,6,7,8,9.5,11.75,13.55,15.5,18.6,20.6,22.6,24.6,
              26.6,28,30,32,34,36,38,40,42,44,46,48,50,55,60])*10**(-6)
        for i in np.linspace(1,40,40):
            GFAS.loc[:,'%.9f'%bins[int(i-1)]]=GFAS.loc[:,'Bin %i'%int(i)]/(GFAS['Flow Vel_blower (m/s)']*0.1749999970198)
        Dpmin=0.3989999890327
        ## calculate dlogdP
        dlogDp=np.log10(GFAS.columns[-40:].astype(float).values)-shift(np.log10(GFAS.columns[-40:].astype(float).values),1,cval=np.nan)
        dlogDp[0]=np.log10(GFAS.columns[-40:].astype(float).values)[0]-np.log10(Dpmin*10**(-6))
        GFAS.iloc[:,-40:]=GFAS.iloc[:,-40:]/dlogDp
        
    return GFAS


# -----------------------------------------------------------------------------

# Read GFAS data
def readGFAS(path=None,starttime=None,endtime=None,timefmt=None,filetype='GFAS_User_Data'):
    ''' Function to read GFAS data

    Takes either the argument path = path to data folder as a string
    or flist = a list of paths for chosen data files as strings

    Returns a dictionary with fields: ...
    '''
    
    from zipfile import ZipFile
    from zipfile import is_zipfile
    
    # check if all input is given
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime and timefmt as input needed...')
    if (filetype!='GFAS_User_Data') and (filetype!='GFAS_Diagnostic_Data'):
        print('filetype has to be GFAS_User_Data or GFAS_Diagnostic_Data')

    flist = [f for f in glob.glob(path + "/*") if timeselect(f,f[-8:],'%Y%m%d',starttime,endtime,timefmt)]

    ## get zipped folders
    dfs=[]
    flists2=[]
    for file in range(len(flist)):
        flist2 = [f for f in glob.glob(flist[file] + "/*") if f[-4:] == '.zip']
        flists2=flists2+flist2  
    i=0
    for file in range(len(flists2)):    
        if is_zipfile(flists2[file])==True:
            try:
                zip_file = ZipFile(flists2[file])
                for text_file in zip_file.infolist():
                    if text_file.filename.endswith('.csv') and text_file.filename.startswith(filetype):
                        i=i+1
                        #print(text_file.filename)
                        df=pd.read_csv(BytesIO(zip_file.open(text_file.filename).read()),usecols=np.linspace(0,84,85).astype(int))
                        df.rename(columns = lambda x: x[0:6] if x.startswith('Bin') else x,inplace=True)
                        df.rename(columns = lambda x: x[0:-1] if x.endswith(' ') else x,inplace=True)
                        df.set_index('Time Stamp (UTC sec)', inplace=True)
                        df['datetime']=pd.to_datetime(dt.datetime(1904,1,1)) + pd.to_timedelta(df.index.values,'s')
                        df.set_index('datetime', inplace=True)
                        dfs.append(df)
            except EmptyDataError:
                print(f"No columns to parse from file {flist[file]}")
    if i>1:
        GFAS_zipped = pd.concat(dfs)
    elif i==1:
        GFAS_zipped = df
    else:
        GFAS_zipped = []
    # get folders that are no zipped folders
    flists3=[]
    for file in range(len(flist)):
        flist3 = [f for f in glob.glob(flist[file] + "/*") if ((f[-4:] != '.zip')&(f[-4:] != '.log'))]
        flists3=flists3+flist3
    flists4=[]
    flists5=[]
    for file in range(len(flists3)):
        #User data:
        flist4 = [f for f in glob.glob(flists3[file] + "/*") if (f.endswith('.csv') and f[-38:-24]==filetype)]
        flists4=flists4+flist4
        #Diagnostic data:
        flist5 = [f for f in glob.glob(flists3[file] + "/*") if (f.endswith('.csv') and f[-44:-24]==filetype)]
        flists5=flists5+flist5
    li = []
    if filetype=='GFAS_User_Data':
        for file in range(len(flists4)):
            df3 = pd.read_csv(flists4[file],usecols=np.linspace(0,84,85).astype(int))
            df3.rename(columns = lambda x: x[0:6] if x.startswith('Bin') else x,inplace=True)
            df3.rename(columns = lambda x: x[0:-1] if x.endswith(' ') else x,inplace=True)
            df3.set_index('Time Stamp (UTC sec)', inplace=True)
            df3['datetime']=pd.to_datetime(dt.datetime(1904,1,1)) + pd.to_timedelta(df3.index.values,'s')
            df3.set_index('datetime', inplace=True)
            li.append(df3)
    elif filetype=='GFAS_Diagnostic_Data':
        for file in range(len(flists5)):
            df3 = pd.read_csv(flists5[file],usecols=np.linspace(0,84,85).astype(int))
            df3.rename(columns = lambda x: x[0:6] if x.startswith('Bin') else x,inplace=True)
            df3.rename(columns = lambda x: x[0:-1] if x.endswith(' ') else x,inplace=True)
            df3.set_index('Time Stamp (UTC sec)', inplace=True)
            df3['datetime']=pd.to_datetime(dt.datetime(1904,1,1)) + pd.to_timedelta(df3.index.values,'s')
            df3.set_index('datetime', inplace=True)
            li.append(df3)
    if (li!=[]):
        GFAS_unzipped = pd.concat(li)
        if (GFAS_zipped!=[]):
            GFAS=pd.concat([GFAS_zipped,GFAS_unzipped],axis=0).sort_index()
        else:
            GFAS=GFAS_unzipped
    else:
        GFAS=GFAS_zipped
    GFAS=GFAS.loc[starttime:endtime]
    if filetype=='GFAS_User_Data':
        bins=np.array([0.5,0.55,0.6,0.65,0.7,0.75,0.8,0.85,0.9,0.95,1,2.65,3.1,5,6,7,8,9.5,11.75,13.55,15.5,18.6,20.6,22.6,24.6,
              26.6,28,30,32,34,36,38,40,42,44,46,48,50,55,60])*10**(-6)
        for i in np.linspace(1,40,40):
            GFAS.loc[:,'%.9f'%bins[int(i-1)]]=GFAS.loc[:,'Bin %i'%int(i)]/(GFAS['Flow Vel_blower (m/s)']*0.1749999970198)
        Dpmin=0.3989999890327
        ## calculate dlogdP
        dlogDp=np.log10(GFAS.columns[-40:].astype(float).values)-shift(np.log10(GFAS.columns[-40:].astype(float).values),1,cval=np.nan)
        dlogDp[0]=np.log10(GFAS.columns[-40:].astype(float).values)[0]-np.log10(Dpmin*10**(-6))
        GFAS.iloc[:,-40:]=GFAS.iloc[:,-40:]/dlogDp

        
    return GFAS

# -----------------------------------------------------------------------------

# Read processed GFAS data
def readprocessedGFAS(path=None,starttime=None,endtime=None,timefmt=None):
    ''' Function to read Igor processed GFAS data

    Takes either the argument path = path to data folder as a string
    or flist = a list of paths for chosen data files as strings

    Returns a dataframe that contains (as for DMPS systems) dN/dlogDp
    '''
    # check if all input is given
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime and timefmt as input needed...')

    flist = [f for f in glob.glob(os.path.join(path, "*/*/ProcessedData/pbpSizeDistributions*")) if timeselect(f,f[-12:-4],'%Y%m%d',starttime,endtime,timefmt)]
    flist_sizes = [f for f in glob.glob(os.path.join(path, "*/*/ProcessedData/pbpSizeThresholds*")) if timeselect(f,f[-12:-4],'%Y%m%d',starttime,endtime,timefmt)]
    flist_derived = [f for f in glob.glob(os.path.join(path, "*/*/ProcessedData/pbpDerivedParameters*")) if timeselect(f,f[-12:-4],'%Y%m%d',starttime,endtime,timefmt)] 
    flist_readGFAS=([f.split('.', 1)[0][-8:] for f in flist])

    for date in range(len(flist_readGFAS)):
        if date==0:
            if pd.to_datetime(flist_readGFAS[date])<pd.to_datetime('20220318'):
                GFAS=readoldGFAS(path="D:/FAIRARI_raw/GFAS 002 Data", starttime=str(pd.to_datetime(flist_readGFAS[date]))[:10],endtime=str(pd.to_datetime(flist_readGFAS[date]))[:10],timefmt='%Y-%m-%d',filetype='GFAS_User_Data*.zip').resample('1S').mean()
            elif pd.to_datetime(flist_readGFAS[date])>pd.to_datetime('20220318'):
                GFAS=readGFAS(path="D:/FAIRARI_raw/GFAS 003 Data", starttime=str(pd.to_datetime(flist_readGFAS[date]))[:10],endtime=str(pd.to_datetime(flist_readGFAS[date]))[:10],timefmt='%Y-%m-%d').resample('1S').mean()
        else:
            if pd.to_datetime(flist_readGFAS[date])<pd.to_datetime('20220318'):
                GFAS_s=readoldGFAS(path="D:/FAIRARI_raw/GFAS 002 Data", starttime=str(pd.to_datetime(flist_readGFAS[date]))[:10],endtime=str(pd.to_datetime(flist_readGFAS[date]))[:10],timefmt='%Y-%m-%d',filetype='GFAS_User_Data*.zip').resample('1S').mean()
            elif pd.to_datetime(flist_readGFAS[date])>pd.to_datetime('20220318'):
                GFAS_s=readGFAS(path="D:/FAIRARI_raw/GFAS 003 Data", starttime=str(pd.to_datetime(flist_readGFAS[date]))[:10],endtime=str(pd.to_datetime(flist_readGFAS[date]))[:10],timefmt='%Y-%m-%d').resample('1S').mean()
            GFAS=pd.concat([GFAS,GFAS_s],axis=0)
    
    for file in range(len(flist)):
        #print(flist[file])
        # Read data file
        if file==0:
            df = pd.read_csv(flist[file],delimiter='\t')
            df['datetime']=pd.to_datetime(df['gfasUserSeconds'], unit='s',origin=pd.to_datetime(flist[file][-12:-4]))
            df.set_index('datetime', inplace=True)
            df=df[~df.index.duplicated(keep='first')].drop(columns=['gfasUserSeconds']).resample('1S').mean()
            if len(df)<86400: # sometimes the processed datafiles are shorter than a day, extend them to a full day with nan values
                df.loc['%s'%(pd.to_datetime(flist[file][-12:-4])+pd.Timedelta('86399S')),:]=np.nan
                df=df.resample('1S').mean()
            df_sizes = pd.read_csv(flist_sizes[file],delimiter='\t',skiprows=1)
            df_sizes.iloc[80] = np.nan
            df_sizes = df_sizes.dropna()
            df_derived = pd.read_csv(flist_derived[file],delimiter='\t')
            df_derived['datetime']=pd.to_datetime(df_derived['gfasUserSeconds'], unit='s',origin=pd.to_datetime(flist_derived[file][-12:-4]))
            df_derived.set_index('datetime', inplace=True)
            df_derived=df_derived[~df_derived.index.duplicated(keep='first')].drop(columns=['gfasUserSeconds']).resample('1S').mean()
            if len(df_derived)<86400: # sometimes the processed datafiles are shorter than a day, extend them to a full day with nan values
                df_derived.loc['%s'%(pd.to_datetime(flist_derived[file][-12:-4])+pd.Timedelta('86399S')),:]=np.nan
                df_derived=df_derived.resample('1S').mean()
        else:
            dfs = pd.read_csv(flist[file],delimiter='\t')
            dfs['datetime']=pd.to_datetime(dfs['gfasUserSeconds'], unit='s',origin=pd.to_datetime(flist[file][-12:-4]))
            dfs.set_index('datetime', inplace=True)
            dfs=dfs[~dfs.index.duplicated(keep='first')].drop(columns=['gfasUserSeconds']).resample('1S').mean()
            if len(dfs)<86400: # sometimes the processed datafiles are shorter than a day, extend them to a full day with nan values
                dfs.loc['%s'%(pd.to_datetime(flist[file][-12:-4])+pd.Timedelta('86399S')),:]=np.nan
                dfs=dfs.resample('1S').mean()
            df=pd.concat([df,dfs],axis=0)
            dfs_derived = pd.read_csv(flist_derived[file],delimiter='\t')
            dfs_derived['datetime']=pd.to_datetime(dfs_derived['gfasUserSeconds'], unit='s',origin=pd.to_datetime(flist_derived[file][-12:-4]))
            dfs_derived.set_index('datetime', inplace=True)
            dfs_derived=dfs_derived[~dfs_derived.index.duplicated(keep='first')].drop(columns=['gfasUserSeconds']).resample('1S').mean()
            if len(dfs_derived)<86400: # sometimes the processed datafiles are shorter than a day, extend them to a full day with nan values
                dfs_derived.loc['%s'%(pd.to_datetime(flist_derived[file][-12:-4])+pd.Timedelta('86399S')),:]=np.nan
                dfs_derived=dfs_derived.resample('1S').mean()
            df_derived=pd.concat([df_derived,dfs_derived],axis=0)
    df.columns=df_sizes.values[:,0]
    df_conc=df.copy()
    for i in np.linspace(0,199,199):
        i=int(i)
        df_conc.iloc[:,i]=df.iloc[:,i]/(GFAS.loc[:,'Flow Vel_blower (m/s)']*df_derived.loc[:,'gfasPbPElapsedSeconds']*0.1749999970198)
    df_H=df_conc.iloc[:,:80]
    df_L=df_conc.iloc[:,80:]

    del df_conc
    df_conc=pd.concat([df_H.iloc[:,:72],df_L.iloc[:,6:]],axis=1) #pd.concat([df_H.iloc[:,:12],df_L.iloc[:,1:]],axis=1), 40,4
    dlogDp=np.log10(df_conc.columns.astype(float).values)-shift(np.log10(df_conc.columns.astype(float).values),1,cval=np.nan)
    dlogDp[0]=np.log10(df_conc.columns.astype(float).values)[0]-np.log10(0.03)

    df_conc=df_conc/dlogDp

    df_conc['Wind Speed (m/s)']=GFAS['Wind Speed (m/s)']
    df_conc['Wind Direction (deg)']=GFAS['Wind Direction (deg)']
    df_conc['Compass Heading (deg)']=GFAS['Compass Heading (deg)']
    df_conc['Flow Vel_blower (m/s)']=GFAS['Flow Vel_blower (m/s)']
    df_conc['Flow M3/m_blower (m3/m)']=GFAS['Flow M3/m_blower (m3/m)']
    df_conc['Laser Current (mA)']=GFAS['Laser Current (mA)']
    
    return df_conc

# -----------------------------------------------------------------------

def readFM120(path=None,starttime=None,endtime=None,timefmt=None):
    ''' Function for reading FM120 data

    Input path, starttime, endtime, and timefmt as strings

    Returns a pandas DataFrame with the chosen fields (see code)
    '''    
# check if all input is given
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime and timefmt as input needed...')

    flist = [f for f in glob.glob(path+'/*/*/00FM*.csv') if timeselect(f,f[-18:-10],'%Y%m%d',starttime,endtime,timefmt)] 
    
    # Initialise DataFrame list
    dfs = []

    # # Loop for reading the data files
    #print('Reading data...')
    for file in range(len(flist)):
        df = pd.read_csv(flist[file], sep=',', header=1, skiprows=96)
        df.index=pd.to_datetime(df['Date']+' '+df['Time'],format='%Y-%m-%d %H:%M:%S')
        df=df.drop(columns=['Year','Day of Year','End Seconds','Date','Time'])
        
        # Append to list of dfs
        dfs.append(df)

        # Print name of data file
        print(flist[file].split('/')[-1])

    # Concatenate the df list to single df
    #print('Concatenating DataFrames...')
    FM120 = pd.concat(dfs)
    
    bins=np.array([3,4,5,6,7,8,9,10,11,12,13,14,16,18,20,22,24,26,28,30,32,34,36,38,40,42,44,46,48,50])*10**(-6)
    for i in np.linspace(1,30,30):
        FM120['%.9f'%bins[int(i-1)]]=FM120['Fog Monitor Bin %i'%int(i)]/(FM120['PAS (m/s)']*0.267)
    Dpmin_FM=2
    ## calculate dlogdP
    dlogDp=np.log10(FM120.columns[-30:].astype(float).values)-shift(np.log10(FM120.columns[-30:].astype(float).values),1,cval=np.nan)
    dlogDp[0]=np.log10(FM120.columns[-30:].astype(float).values)[0]-np.log10(Dpmin_FM*10**(-6))
    FM120.iloc[:,-30:]=FM120.iloc[:,-30:]/dlogDp
    
    FM120=FM120.loc[starttime:endtime]
    return FM120

# -----------------------------------------------------------------------------

# Read Hygrometer data
def readHygrometer(path=None,starttime=None,endtime=None,timefmt=None,filetype=None):
    ''' Function to read Hygrometer data

    Takes either the argument path = path to data folder as a string
    or flist = a list of paths for chosen data files as strings

    Returns a dictionary with fields: ...
    '''
    
    # check if all input is given
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime and timefmt as input needed...')

    flist = [f for f in glob.glob(path + "/Hygro_*.txt") if timeselect(f,f[-14:-4],'%Y-%m-%d',starttime,endtime,timefmt)]
    print(flist)
    
    #### read data and save to dataframe Data, 
    li = []
    for filename in flist:
        #print(filename)
        df = pd.read_csv(filename,
                         names=['date','time','sys_time','h2o_final','h2o_strong','h2o_weak','p',
                            'temp_cell','temp_el','temp_spare','2f_strong','laser_strong',
                           'id_strong','2f_weak','laser_weak','id_weak','zero_level'],
                         delimiter= '\s+',header=None)
        li.append(df)

    Data = pd.concat(li, axis=0, ignore_index=True)
    Data.index=pd.to_datetime(Data['date'] + ' ' + Data['time'],format='%Y-%m-%d %H:%M:%S')
    Data=Data.loc[starttime:endtime]
    
    return Data


# -----------------------------------------------------------------------------

# Function for reading MPS data
def readMPS(path=None,starttime=None,endtime=None,timefmt=None):
    ''' Function for reading MSP data

    Takes either the argument path = path to data folder as a string
    or flist = a list of paths for chosen data files as strings

    Returns a pandas DataFrame
    '''
    if (path is None) or (starttime is None) or (endtime is None) or (timefmt is None):
        print('path, starttime, endtime and timefmt as input needed...')

    flist = [f for f in glob.glob(os.path.join(path, "*/*/00MPS*.csv")) if (timeselect(f,f[-47:-39],'%Y%m%d',starttime,endtime,timefmt))]
    # Empty list to fill with dfs
    MPS = []

    for i, file in enumerate(flist):
	# Read file
        df = pd.read_csv(file, sep=',',header=91)
        # Make datetime index and drop those columns (plus the weird empty column)
        df.index = pd.to_datetime(df['Date'] + ' ' + df['Time'], format='%Y-%m-%d %H:%M:%S')
        df.drop(['Time','Date'], axis=1, inplace=True)
        
	# Append dfs to list
        MPS.append(df)

    # Concatenate dfs
    MPS = pd.concat(MPS)
    
    
    MPS=MPS.loc[starttime:endtime]
    
    return MPS

