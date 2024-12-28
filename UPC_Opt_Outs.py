"""
This script is used to obtain opt-out information for a series of patent numbers from the UPC patent database.
Requires .xlsx input file with 'Patent Number' column and output path. See lines 131 and 132.
"""

import requests
import pprint as pp
import json
import pandas as pd
import time
import datetime

# URLs
BASE_URL = 'https://api-prod.unified-patent-court.org/upc/public/api/v4/opt-out/list?patentNumber='
SPIKE_VIOLATION = "{'fault': {'faultstring': 'Spike arrest violation. " 'Allowed rate : MessageRate{messagesPerPeriod=60, ' "periodInMicroseconds=60000000, maxBurstMessageCount=6.0}', 'detail': " "{'errorcode': 'policies.ratelimit.SpikeArrestViolation'}}}"
GATEWAY_TIMEOUT = "{'fault': {'faultstring': 'Gateway Timeout', 'detail': " "{'errorcode': 'messaging.adaptors.http.flow.GatewayTimeout', 'reason': " "'TARGET_READ_TIMEOUT'}}}"

def main(patent_excel, output_folder):

    date_now = datetime.datetime.now().strftime('%Y-%m-%d %H%M')

    patent_offset = 0

    # read excel
    patent_data = pd.read_excel(patent_excel, names = ['Patent Number'])

    # create copy for 'latest only' record df
    patent_data_latest = patent_data.copy(deep = True)
    
    # get list of patent numbers
    patent_numbers = patent_data['Patent Number'].tolist()
    
    # drop patent numbers from df
    patent_data.drop('Patent Number', inplace = True, axis = 1)

    # add columns to dataframe
    patent_data['Patent Number'], patent_data['Case Type'], patent_data['Lodging Date'], patent_data['Case Number'], patent_data['Outcome'] = '', '', '', '', ''

    # iterate over patent_data df and get each response
    for patent in range(len(patent_numbers)):
        
        request_code = 0
        print('patent #: ' + str(patent_numbers[patent]))

        while (str(request_response) == SPIKE_VIOLATION or str(request_response) == GATEWAY_TIMEOUT):
            
            time.sleep(1)
            
            try:
                request_response, request_code = json.loads(requests.get(BASE_URL + patent_numbers[patent].strip()).text), requests.get(BASE_URL + patent_numbers[patent].strip()).status_code
                pp.pprint('response (length: ' + str(len(request_response)) + '):\n' + str(request_response) + '\nrequest code: ' + str(request_code))

            except:
                print(request_code)
                pass

        # empty response
        if(str(request_response) == '' or str(request_response) == '[]'):
           
            patent_data.at[patent + patent_offset, 'Patent Number'] = patent_numbers[patent]
            patent_data.at[patent + patent_offset, 'Case Type'] = ''
            patent_data.at[patent + patent_offset, 'Lodging Date'] = ''
            patent_data.at[patent + patent_offset, 'Case Number'] = ''
            patent_data.at[patent + patent_offset, 'Outcome'] = ''

            patent_data_latest.at[patent, 'Case Type'] = ''
            patent_data_latest.at[patent, 'Lodging Date'] = ''
            patent_data_latest.at[patent, 'Case Number'] = ''
            patent_data_latest.at[patent, 'Outcome'] = ''

            continue

        # single response
        elif (len(request_response) == 1):

            patent_data.at[patent + patent_offset, 'Patent Number'] = patent_numbers[patent]
            patent_data.at[patent + patent_offset, 'Case Type'] = request_response[0]['caseType']
            patent_data.at[patent + patent_offset, 'Lodging Date'] = request_response[0]['dateOfLodging']
            patent_data.at[patent + patent_offset, 'Case Number'] = request_response[0]['caseNumber']
            patent_data.at[patent + patent_offset, 'Outcome'] = request_response[0]['outcome']

            patent_data_latest.at[patent, 'Case Type'] = request_response[0]['caseType']
            patent_data_latest.at[patent, 'Lodging Date'] = request_response[0]['dateOfLodging']
            patent_data_latest.at[patent, 'Case Number'] = request_response[0]['caseNumber']
            patent_data_latest.at[patent, 'Outcome'] = request_response[0]['outcome']

            continue

        # multiple responses
        else:

            latest_date = datetime.datetime(1, 1, 1)

            for response in range(len(request_response)):

                patent_data.at[patent + patent_offset, 'Patent Number'] = patent_numbers[patent]
                patent_data.at[patent + patent_offset, 'Case Type'] = request_response[response]['caseType']
                patent_data.at[patent + patent_offset, 'Lodging Date'] = request_response[response]['dateOfLodging']
                patent_data.at[patent + patent_offset, 'Case Number'] = request_response[response]['caseNumber']
                patent_data.at[patent + patent_offset, 'Outcome'] = request_response[response]['outcome']

                # increment offset to account for multiple responses
                patent_offset += 1

                response_date = datetime.datetime.strptime(request_response[response]['dateOfLodging'], '%Y-%m-%d %H:%M:%S')

                if response_date > latest_date:
                    latest_date = response_date

                    patent_data_latest.at[patent, 'Case Type'] = request_response[response]['caseType']
                    patent_data_latest.at[patent, 'Lodging Date'] = request_response[response]['dateOfLodging']
                    patent_data_latest.at[patent, 'Case Number'] = request_response[response]['caseNumber']
                    patent_data_latest.at[patent, 'Outcome'] = request_response[response]['outcome']

                else:
                    pass

            patent_offset -= 1
            
    # sort dataframes
    patent_data = patent_data.sort_values(['Patent Number', 'Lodging Date'], ascending = [True, True])
    patent_data_latest = patent_data_latest.sort_values(['Patent Number'], ascending = [True])

    # transform df into excel
    writer = pd.ExcelWriter(path = output_folder + str(date_now) + '.xlsx', engine = 'xlsxwriter')
    patent_data_latest.to_excel(writer, sheet_name = 'Latest', index = None)
    patent_data.to_excel(writer, sheet_name = 'Historical', index = None)
    writer.close()

if __name__ == "__main__":
    patent_excel = r''
    output_folder = r''
    main(patent_excel, output_folder)