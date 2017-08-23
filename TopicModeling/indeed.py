
# coding: utf-8

# In[1]:

# load the library
from bs4 import BeautifulSoup as Soup
import urllib, requests, re, pandas as pd


# In[2]:

#Step 1: jobsearch url

BASE_URL = 'http://www.indeed.com'

def jobsearch_url(query, location):
    '''
    Args:
        query (string): jobsearch query
        location (string): location of jobsearch including city, state 
                            Ex: Austin, TX 

    Returns:
        string: jobsearch url
    
    '''
    #jobsearch addition to base url
    js_url = '/jobs?'
    
    #query addition to base url
    q_list = query.split()
    q = '+'.join(q_list)
    job_query = 'q=' + q
    
    #job location addition to base url
    l_list = location.split(',') #will provide [city, st]

    state_list = str(l_list[1]).strip()

    state = '%2C+'+ state_list

    city_list = l_list[0].split()
    city = '+'.join(city_list)

    job_location = '&l=' + city + state

    js_url = BASE_URL + js_url + job_query + job_location
    
    return js_url


# In[3]:

#Step 2: get information on results from jobsearch

def get_jobs(js_url):
    '''
    Args:
        js_url (string): formatted jobsearch url link

    Returns:
        pandas df: dataframe with details of each job
    
    '''    
    #we will go over the results of each page and append results to result dataframe
    jobs_df = pd.DataFrame()
    
    js_soup = Soup(urllib.urlopen(js_url), "lxml")
    home_url = "http://www.indeed.com"
    
    #to go over each page, the url changes to js_url+'&start=10' in increments of 10
    # Ex: https://www.indeed.com/jobs?q=developer&l=AUstin,+tx&start=0
    #     https://www.indeed.com/jobs?q=developer&l=AUstin,+tx&start=10
    for js_count in range(0, 110, 10): #get 100 jobs
        js_page_url = js_url + '&start=' + str(js_count)
        
        js_soup = Soup(urllib.urlopen(js_page_url), "lxml")
        
        # find target for every job on the page
        job_rows = js_soup.findAll('div', attrs={'class' : '  row  result'}) 
        
        # find company name, job title, job url, address, num of days since posted. Also, 
        # find company link if available
        for cur_job in job_rows: 
            comp_name = cur_job.find('span', attrs={'itemprop':'name'}).getText().strip()
            job_title = cur_job.find('a', attrs={'class':'turnstileLink'}).attrs['title']
            job_link = "%s%s" % (home_url,cur_job.find('a').get('href'))
            job_addr = cur_job.find('span', attrs={'itemprop':'addressLocality'}).getText()
            job_posted = cur_job.find('span', attrs={'class': 'date'}).getText()
            comp_page_link = cur_job.find('span', attrs={'itemprop':'name'}).find('a')
            
            # if company link exists, access it. Otherwise, skip.
            if comp_page_link != None: 
                comp_page_link = "%s%s" % (home_url, comp_page_link.attrs['href'])
                company_reviews_link = comp_page_link + '/reviews'
            else: 
                comp_page_link = None
                company_reviews_link = None
                
            # add a job info to our data frame
            jobs_df = jobs_df.append({'comp_name': comp_name, 
                                      'job_title': job_title, 
                                      'job_link': job_link, 
                                      'job_posted': job_posted,
                                      'comp_page_link': comp_page_link, 
                                      'company_reviews_link' : company_reviews_link, 
                                      'job_location': job_addr}, ignore_index=True)
    return jobs_df


# In[4]:

#Step 3: get information on ratings of each company returned from jobsearch results
def get_comp_ratings(jobs_df):
    '''
    Args:
        jobs_df (dataframe): jobs

    Returns:
        pandas df: dataframe with ratings on work-life balance, 
                   pay & benefits, job security & advancement, 
                   management and culture
    '''  
    #add columns to capture the individual ratings
    jobs_df['comp_rating_overall'] = None
    jobs_df['culture_rating'] = None
    jobs_df['comp_rating_overall'] = None
    jobs_df['wl_bal_rating'] = None
    jobs_df['js_adv_rating'] = None
    jobs_df['mgmt_rating'] = None

    for index, row in jobs_df.iterrows():
        if row['comp_page_link'] is not None:
            comp_name = row['comp_name']
            comp_page_url = row['comp_page_link'].strip()
#             print 'comp_page_url', comp_page_url
            comp_page = Soup(urllib.urlopen(comp_page_url), "lxml")

            #find all the ratings of given company
            comp_page_content = comp_page.find('div', {'class' : 'cmp-OverallRating-average'})
            
            if comp_page_content is not None:
                comp_rating_overall = float(comp_page_content.get_text().strip())            
                jobs_df.loc[jobs_df.comp_name == comp_name, 'comp_rating_overall'] = comp_rating_overall

                #find values of all the ratings
                rating_values = comp_page.findAll('span', {'class' : 'cmp-ReviewCategories-rating'})

                if rating_values is not None:
                    culture_rating = float(rating_values[0].get_text().strip())
                    jobs_df.loc[jobs_df.comp_name == comp_name, 'culture_rating'] = culture_rating

                    compens_ben_rating = float(rating_values[1].get_text().strip())
                    jobs_df.loc[jobs_df.comp_name == comp_name, 'comp_rating_overall'] = comp_rating_overall

                    wl_bal_rating = float(rating_values[2].get_text().strip())
                    jobs_df.loc[jobs_df.comp_name == comp_name, 'wl_bal_rating'] = wl_bal_rating

                    js_adv_rating = float(rating_values[3].get_text().strip())
                    jobs_df.loc[jobs_df.comp_name == comp_name, 'js_adv_rating'] = js_adv_rating

                    mgmt_rating = float(rating_values[4].get_text().strip())
                    jobs_df.loc[jobs_df.comp_name == comp_name, 'mgmt_rating'] = mgmt_rating

    return jobs_df


# In[5]:

#Step 4: get information on reviews of each company returned from jobsearch results
def get_reviews(jobs_df):
    '''
    Args:
        jobs_df (dataframe): jobs

    Returns:
        pandas df: dataframe with reviews and rating for each review
    ''' 
    #add columns to capture the individual ratings
    reviews_df = pd.DataFrame()
    
    for index, row in jobs_df.iterrows():
        if row['company_reviews_link'] is not None:
            comp_name = row['comp_name']
            comp_review_page_url = row['company_reviews_link'].strip()
    #             print 'comp_review_page_url', comp_review_page_url
            review_page = Soup(urllib.urlopen(comp_review_page_url), "lxml")
            num_reviews_txt = review_page.find('div', {'class' : 'cmp-filter-result'}).get_text()
            num_reviews = int(re.sub('[a-zA-z,]', '',num_reviews_txt).strip())
            jobs_df.loc[jobs_df.comp_name == comp_name, 'num_reviews'] = num_reviews
            num_review_pages = num_reviews / 20 #there are 20 reviews per page

            #for our analysis, we will only collect max of 100 reviews for each company, 
            # so cap off num_review_pages = 5 as each page has 20 reviews           
            if num_review_pages > 5:
                num_review_pages = 5

            for page in range(num_review_pages):
                review_cnt_var = num_review_pages * 20
                comp_review_page_url = comp_review_page_url + '?start=' + str(review_cnt_var)
                comp_reviews_page = Soup(urllib.urlopen(comp_review_page_url), "lxml")

                #find text of all the reviews, pros and cons of given company
                comp_reviews_content = comp_reviews_page.findAll('span', {'class' : 'cmp-review-text'})
                
                for content in comp_reviews_content:
                    cur_review_text = content.get_text()
                    reviews_df = reviews_df.append({'comp_name' : comp_name, 'review_text' : cur_review_text}, ignore_index = True)
#                 pros_content = comp_reviews_page.findall('div', {'class': 'cmp-review-pro-text'})
#                 cons_content = comp_reviews_page.findall('div', {'class': 'cmp-review-con-text'})
    reviews_df.drop_duplicates(['comp_name', 'review_text'], inplace = True)
    return reviews_df       


# In[6]:

def get_cmp_details(jobs_df):
        '''
        Args:
            jobs_df (dataframe): jobs

        Returns:
            pandas df: dataframe with company_name, HQ location, revenue,
                       employee count and industry it belongs to
        ''' 
        comp_name = jobs_df['comp_name'].unique().tolist()
        print len(comp_name)
        for name in comp_name:
            comp_page_url = jobs_df.loc[jobs_df.comp_name == name, 'comp_page_link'].values[0]
             
            if comp_page_url is not None:
                comp_page_content = Soup(urllib.urlopen(comp_page_url), 'lxml')
                
                if comp_info_content is not None:
                    comp_info_content = comp_page_content.find('dl', {'id' : 'cmp-company-details-sidebar'}).findAll('dd')

                    if comp_info_content is not None:
                        try:
                            hq_loc = comp_info_content[0].get_text()
                            jobs_df.loc[jobs_df.comp_name == name, 'hq_loc'] = hq_loc
                        except: 
                            jobs_df.loc[jobs_df.comp_name == name, 'hq_loc'] = None

                        try:
                            comp_rev = comp_info_content[1].get_text()
                            jobs_df.loc[jobs_df.comp_name == name, 'comp_rev'] = comp_rev
                        except:
                            jobs_df.loc[jobs_df.comp_name == name, 'comp_rev'] = None

                        try:
                            emp_cnt = comp_info_content[2].get_text()
                            jobs_df.loc[jobs_df.comp_name == name, 'emp_cnt'] = emp_cnt
                        except: 
                            jobs_df.loc[jobs_df.comp_name == name, 'emp_cnt'] = None

                        try:
                            comp_industry = comp_info_content[3].get_text()
                            jobs_df.loc[jobs_df.comp_name == name, 'comp_industry'] = comp_industry
                        except:
                            jobs_df.loc[jobs_df.comp_name == name, 'comp_industry'] = None

        return jobs_df


# In[ ]:



