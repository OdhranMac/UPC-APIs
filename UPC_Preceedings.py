"""
This script obtains 'preceedings' information for all UPC database entries within the last three weeks.
Requires output path (line 235) for output .xlsx.
"""

import requests
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from math import ceil

# URLs
BASE_URL = 'https://api-prod.unified-patent-court.org/upc/public/api/v4/cases'
SPIKE_VIOLATION = "{'fault': {'faultstring': 'Spike arrest violation. " 'Allowed rate : MessageRate{messagesPerPeriod=60, ' "periodInMicroseconds=60000000, maxBurstMessageCount=6.0}', 'detail': " "{'errorcode': 'policies.ratelimit.SpikeArrestViolation'}}}"
GATEWAY_TIMEOUT = "{'fault': {'faultstring': 'Gateway Timeout', 'detail': " "{'errorcode': 'messaging.adaptors.http.flow.GatewayTimeout', 'reason': " "'TARGET_READ_TIMEOUT'}}}"

def main():

    total_results_response_code = -1
    cumulative_results = pd.DataFrame()
    date_now = datetime.now().strftime('%Y-%m-%d %H%M')

    # get 'three weeks ago'
    threshold = datetime.strftime(datetime.today() - timedelta(days = 21), '%Y-%m-%d')
  
    # send inital request and find out number of results in the last three weeks - use as 'for i in range(x)'
    while (total_results_response_code != 200 or str(total_results) == SPIKE_VIOLATION or str(total_results) == GATEWAY_TIMEOUT):
        try:
            total_results, total_results_response_code = json.loads(requests.get(BASE_URL + '?receiptDateFrom=' + str(threshold) + '&pageSize=1').text)['totalResults'], requests.get(BASE_URL + '?receiptDateFrom=' + str(threshold)).status_code
        except:
            pass

    # calculate number of pages to fetch from API
    num_of_pages = ceil(total_results / 100)
 
    # iterate over number of pages
    for i in range(num_of_pages):

        request_code = -1
        page_num = i + 1

        while (request_code != 200 or str(request_response) == SPIKE_VIOLATION or str(request_response) == GATEWAY_TIMEOUT):
            try:
                request_response, request_code = json.loads(requests.get(BASE_URL + '?pageSize=100&receiptDateFrom=' + str(threshold) + '&pageNumber=' + str(page_num)).text), requests.get(BASE_URL).status_code
            except:
                pass        
 
        # store page results in dataframe
        page_results = pd.DataFrame(data = request_response['content'])

        # create new columns
        page_results['Title'] = ''
        page_results['Patent Number'] = ''
        page_results['Court'] = ''
        page_results['Representatives'] = ''
        page_results['Parties'] = ''
        page_results['Judges'] = ''
        page_results['IPC Classification'] = ''
        page_results['Value'] = ''

        # stores indices to drop
        drop_list = np.array([])
        
        #print(len(page_results))
        num_of_rows = len(page_results)

        # for each row in page_results
        for i in range(num_of_rows):

            """ Court """
            try:
                page_results.at[i, 'Court'] = str(page_results.iloc[i]['division']['courtType']) + '\n' + str(page_results.iloc[i]['division']['divisionType'])
            except:
                pass

            """ Representatives and Parties """
            parties = page_results.iloc[i]['parties']

            # claimant, defendant and applicant reps
            claimant_reps, defendant_reps, applicant_reps, claimant_parties, defendant_parties, applicant_parties = '', '', '', '', '', ''
            defendant_index, claimant_index, applicant_index = 1, 1, 1

            # iterate over parties and add them to relevant variable
            for party in range(len(parties)):

                if str(parties[party]['companyName']) == 'None':
                    companyName = '[Company not provided]'
                else:
                    companyName = str(parties[party]['companyName'])

                if (str(parties[party]['name']) == 'None' or str(parties[party]['surname']) == 'None'):
                    partyName = '[Name not provided]'
                else:
                    partyName = str(parties[party]['name']) + ' ' + str(parties[party]['surname'])

                if parties[party]['type'].upper() == 'DEFENDANT':
                    defendant_reps += str(defendant_index) + '. ' + partyName + ' (' + companyName + ')\n'
                    defendant_parties += str(defendant_index) + '. ' + companyName + '\n'
                    defendant_index += 1
                
                elif parties[party]['type'].upper() == 'CLAIMANT':
                    claimant_reps += str(claimant_index) + '. ' + partyName + ' (' + companyName + ')\n'
                    claimant_parties += str(claimant_index) + '. ' + companyName + '\n'
                    claimant_index += 1

                elif parties[party]['type'].upper() == 'APPLICANT':
                    applicant_reps += str(applicant_index) + '. ' + partyName + ' (' + companyName + ')\n'
                    applicant_parties += str(applicant_index) + '. ' + companyName + '\n'
                    applicant_index += 1
                
            defendant_reps = defendant_reps.strip()
            claimant_reps = claimant_reps.strip()
            applicant_reps = applicant_reps.strip()

            combined_reps = ''
            
            # combine all reps into one field
            if claimant_reps != '':
                combined_reps +=  'Claimants:\n' + claimant_reps + '\n\n'

            if defendant_reps != '':
                combined_reps +=  'Defendants:\n' + defendant_reps + '\n\n'

            if applicant_reps != '':
                combined_reps +=  'Applicants:\n' + applicant_reps

            page_results.at[i, 'Representatives'] =  combined_reps.strip()
            
            claimant_parties = claimant_parties.strip()
            defendant_parties = defendant_parties.strip()

            if claimant_parties != '' and defendant_parties != '':
                page_results.at[i, 'Parties'] =  claimant_parties + '\n\nV\n\n' + defendant_parties
                

            """ Judges """
            judges = ''

            if page_results.iloc[i]['judges'] == []:
                pass
            
            else:

                judge_index = 1

                for judge in page_results.iloc[i]['judges']:
                    judges += judge
                    
                    if (judge_index < len(judges)):
                        judges += '\n'
                        judge_index += 1
            
            page_results.at[i, 'Judges'] = judges


            """ Get all patent numbers per row """
            patent_list = np.array([])
            patent_desc_list = np.array([])
            
            patents = len(page_results.iloc[i]['patents'])

            # get all patent numbers from row
            for patent in range(patents):
                
                # append to patent_list array
                patent_list = np.append(patent_list, page_results.iloc[i]['patents'][patent]['number'])

                # append to patent_desc_list array
                patent_desc_list = np.append(patent_desc_list, page_results.iloc[i]['patents'][patent]['description'])

            # number of patents can be zero
            if len(patent_list) == 0:
                page_results.at[i, 'Patent Number'] = ''
                page_results.at[i, 'Title'] = ''
            
            # number of patents can be one
            elif len(patent_list) == 1:
                page_results.at[i, 'Patent Number'] = patent_list[0]
                page_results.at[i, 'Title'] = patent_desc_list[0]
            
            # number of patents can be one+
            else:

                # add index to drop_list
                drop_list = np.append(drop_list, i)

                temp_results = pd.DataFrame(columns = page_results.columns)

                for j in range(len(patent_list)):

                    # add row to df
                    temp_results.loc[j] = page_results.iloc[i]

                    # update patent num
                    temp_results.at[j, 'Patent Number'] = patent_list[j]
                
                    # update title
                    temp_results.at[j, 'Title'] = patent_desc_list[j]

                # add temp_results to page_results
                page_results = pd.concat([page_results, temp_results], ignore_index = True)

        drop_list = np.flip(drop_list)
        
        # drop original rows with multi-patents
        for drop_index in range(len(drop_list)):
            page_results = page_results.drop(index = drop_list[drop_index])


        # add page_results to cumulative df
        cumulative_results = pd.concat([cumulative_results, page_results])


    # drop irrelevant columns
    cumulative_results = cumulative_results.drop('decision', axis = 1)
    cumulative_results = cumulative_results.drop('spcs', axis = 1)
    cumulative_results = cumulative_results.drop('number', axis = 1)
    cumulative_results = cumulative_results.drop('year', axis = 1)
    cumulative_results = cumulative_results.drop('patents', axis = 1)
    cumulative_results = cumulative_results.drop('division', axis = 1)
    cumulative_results = cumulative_results.drop('judges', axis = 1)

    # rename columns
    cumulative_results = cumulative_results.rename(columns = {'type': 'Type', 'fullNumber': 'Action Number', 'creationDate': 'Filing Date', 'receiptDate': 'Receipt Date', 'language': 'Language'})

    # rearrange columns
    cumulative_results = cumulative_results.reindex(columns = ['Type', 'Action Number', 'Parties', 'Patent Number', 'Title', 'Language', 'Filing Date', 'Receipt Date', 'Court', 'Representatives', 'Judges', 'IPC Classification', 'Value'])

    # strip time from date columns
    cumulative_results['Filing Date'] = pd.to_datetime(cumulative_results['Filing Date']).dt.date
    cumulative_results['Receipt Date'] = pd.to_datetime(cumulative_results['Receipt Date']).dt.date

    # consolidated df to excel
    cumulative_results.to_excel(r'[OUTPUT PATH HERE]' + str(date_now) + '.xlsx', index = False)

if __name__ == "__main__":
    main()