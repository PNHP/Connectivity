library(data.table)
library(dplyr)
library(sf)

folder = 'H:/Projects/Connectivity_PennDOT'
setwd(folder)
crash_files = list.files(folder,pattern="^CRASH")

crash_df <- data.frame(CRN=numeric(0), DEC_LAT=numeric(0), DEC_LONG=numeric(0), MONTH=character(), DAY=character(), YEAR=character(), TIME=character())
for (i in 1:length(crash_files)){
  tmp <- fread(crash_files[i])
  crash_df <- rbind(crash_df, tmp[, c("CRN", "DEC_LAT", "DEC_LONG", "CRASH_MONTH", "DAY_OF_WEEK", "CRASH_YEAR", "TIME_OF_DAY")])
}

flag_files = list.files(folder,pattern="^FLAG")

flag_df <- data.frame(CRN=numeric(0),RELATED=numeric(0),HIT=numeric(0),SUDDEN=numeric(0))
for(i in 1:length(flag_files)){
  tmp <- fread(flag_files[i])
  flag_df <- rbind(flag_df, tmp[, c("CRN","DEER_RELATED","HIT_DEER","SUDDEN_DEER")])
}

df <- inner_join(crash_df,flag_df,by="CRN")

df_filtered <- filter(df,(DEER_RELATED==1|HIT_DEER==1|SUDDEN_DEER==1)&(!is.na(DEC_LAT)&!is.na(DEC_LONG)))

deer_sf <- st_as_sf(df_filtered, coords = c("DEC_LONG", "DEC_LAT"), crs = 4326)
customalbers <- "+proj=aea +lat_1=40 +lat_2=42 +lat_0=39 +lon_0=-78 +x_0=0 +y_0=0 +ellps=GRS80 +units=m +no_defs "
deer_sf <- st_transform(deer_sf,crs=customalbers)
st_write(deer_sf,"deer_hit_locations1.shp")
