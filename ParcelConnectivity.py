#-------------------------------------------------------------------------------
# Name:        ParcelConnectivity.py
# Purpose:     Prioritize parcels based on connectivity
#
# Author:      MMoore
#
# Created:     08/04/2020
# Updated:
#-------------------------------------------------------------------------------

#import packages to be used in script
import os, arcpy, time
start_time = time.time()

######################################################################################################################################################
#SET PATHS BELOW
######################################################################################################################################################
ccc = r'C:\\_connectivity\\connectivity.gdb\\CCC_Final' # path to cores and connectivity layer
#parcels = r'C:\\_connectivity\\connectivity.gdb\\LH_parcels' # path to parcel layer to be prioritized
parcels = r'C:\_connectivity\connectivity.gdb\Parcels_unified'
output_parcels = r'C:\\_connectivity\\connectivity.gdb\\parcels_final_all' # path and name for output parcel layer that will contain prioritization information
######################################################################################################################################################

#set environments to overwirte outputs and workspace to memory
arcpy.env.overwriteOutput = True
arcpy.env.workspace = "in_memory"

#copy parcel layer to final feature class where calculations will be made
parcels_final = arcpy.FeatureClassToFeatureClass_conversion(parcels,os.path.dirname(output_parcels),os.path.basename(output_parcels))

#add acre field and calculate acres of parcel to be used later in proportion calculation
arcpy.AddField_management(parcels_final,"acres_parcel","DOUBLE","","","","Acres")
with arcpy.da.UpdateCursor(parcels_final,["acres_parcel","SHAPE@"]) as cursor:
    for row in cursor:
        area = row[1].getArea('GEODESIC','ACRES')
        row[0] = area
        cursor.updateRow(row)

#intersect cores and connectors layer with parcels layer
intersect = arcpy.Intersect_analysis([ccc,parcels_final],os.path.join("in_memory","intersect"))

#add acre field to intersect and calculate acres of intersected area
arcpy.AddField_management(intersect,"acres_ccc","DOUBLE","","","","Acres CCC")
with arcpy.da.UpdateCursor(intersect,["acres_ccc","SHAPE@"]) as cursor:
    for row in cursor:
        area = row[1].getArea('GEODESIC','ACRES')
        row[0] = area
        cursor.updateRow(row)

#calculate sum of acres and max of 6 other values
statistics = arcpy.Statistics_analysis(intersect,os.path.join("in_memory","statistics"),[["acres_ccc","SUM"],["Connectivity_Value","MAX"],["NHA_Mean","MAX"],["GeoPhys_Mean","MAX"],["LCM_Mean","MAX"],["RegFlow_Mean","MAX"],["Resilience_Mean","MAX"]],"FID_"+os.path.basename(output_parcels))

#join statistics fields to parcel layer
oid_fieldname = arcpy.Describe(parcels_final).OIDFieldName
arcpy.JoinField_management(parcels_final,oid_fieldname,statistics,"FID_"+os.path.basename(output_parcels),["SUM_acres_ccc","MAX_Connectivity_Value","MAX_NHA_Mean","MAX_GeoPhys_Mean","MAX_LCM_Mean","MAX_RegFlow_Mean","MAX_Resilience_Mean"])

#add 4 fields to store calculations
f_name = ["CCC_pct","CCC_area_score","CCC_priority_score","priority_score_norm","conn_priority"]
f_type = ["DOUBLE","SHORT","DOUBLE","DOUBLE","TEXT"]
f_alias = ["CCC Area Proportion","CCC Area Score","Connectivity Priority Score","CCC Priority Score Normal","Connectivity Priority"]
f_length = ["","","","",20]

for n,t,a,l in zip(f_name,f_type,f_alias,f_length):
    arcpy.AddField_management(parcels_final,n,t,"","",l,a)

#fill SUM_acres with 0 if value is Null
with arcpy.da.UpdateCursor(parcels_final,"SUM_acres_ccc") as cursor:
    for row in cursor:
        if row[0] is None:
            row[0] = 0
            cursor.updateRow(row)

#calculate proportion of parcel area covered by CCC and update field
with arcpy.da.UpdateCursor(parcels_final,["SUM_acres_ccc","acres_parcel","CCC_pct"]) as cursor:
    for row in cursor:
        row[2] = round(row[0]/row[1],3)
        cursor.updateRow(row)

#calculate CCC area score and update field
with arcpy.da.UpdateCursor(parcels_final,["SUM_acres_ccc","CCC_area_score"]) as cursor:
    for row in cursor:
        if row[0] < 0.5:
            score = 0
        elif row[0] >= 0.5 and row[0] <= 1:
            score = 1
        elif row[0] > 1 and row[0] <= 5:
            score = 2
        elif row[0] > 5 and row[0] <= 10:
            score = 3
        elif row[0] > 10 and row[0] <= 25:
            score = 4
        elif row[0] > 25 and row[0] <= 50:
            score = 5
        elif row[0] > 50 and row[0] <= 100:
            score = 6
        elif row[0] > 100 and row[0] <= 250:
            score = 7
        elif row[0] > 250 and row[0] <= 500:
            score = 8
        elif row[0] > 500 and row[0] <= 1000:
            score = 9
        elif row[0] > 1000:
            score = 10
        else:
            pass
        row[1] = score
        cursor.updateRow(row)

#calculate CCC Priority Score by multiplying CCC Area Score, CCC Percent, and Max Connectivity Value
with arcpy.da.UpdateCursor(parcels_final,["CCC_priority_score","CCC_area_score","CCC_pct","MAX_Connectivity_Value"]) as cursor:
    for row in cursor:
        row[0] = round(row[1]*row[2]*row[3],3)
        cursor.updateRow(row)

#find min and max priority scores for normalization equation
with arcpy.da.SearchCursor(parcels_final,"CCC_priority_score") as cursor:
     value_list = sorted({row[0] for row in cursor})
max_value = max(value_list)
min_value = min(value_list)

#calculate normalized priority score
with arcpy.da.UpdateCursor(parcels_final,["priority_score_norm","CCC_priority_score"]) as cursor:
    for row in cursor:
        row[0] = round((row[1]-min_value)/(max_value-min_value),3)
        cursor.updateRow(row)

#calculate priority category for parcels
with arcpy.da.UpdateCursor(parcels_final,["conn_priority","priority_score_norm"]) as cursor:
    for row in cursor:
        if row[1] == 0:
            row[0] = "Very Low"
            cursor.updateRow(row)
        elif row[1] > 0 and row[1] <= 0.3:
            row[0] = "Low"
            cursor.updateRow(row)
        elif row[1] > 0.3 and row[1] <= 0.6:
            row[0] = "Medium"
            cursor.updateRow(row)
        elif row[1] > 0.6 and row[1] <= 0.8:
            row[0] = "High"
            cursor.updateRow(row)
        elif row[1] > 0.8 and row[1] <= 1:
            row[0] = "Very High"
            cursor.updateRow(row)
        else:
            pass

Time = "The script took {} minutes to run.".format(str((time.time()-start_time)/60))
print(Time)