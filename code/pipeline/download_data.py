import csv
import os
import requests
import ast
import tarfile
import time
import json
import gzip
import pandas as pd

username = 'unc_networks'
password = 'UNCSTATS'


def download_court_data(court_name, data_dir):
    """
    Downloads the cluster and opinion files from a given court.

    If the cases are already all downloaded then skips the download. Otherwise
    this function downloads the .gzip file, unzips it then deletes the .gzip
    file.

    Parameters
    ----------
    court_name: string representing the court_name

    data_dir: path to the data directory

    get_clusters: if True then will download the cluster files

    get_opinions: if True then will download the opinion files

    Notes
    ----
    from download_data import download_court_data
    court_name, data_dir = 'nced', '../data/'
    download_court_data(court_name, data_dir)
    """
    # TODO: create csv file containing all court names
    # check court_name is valid court name
    # with open('all_courts.csv', 'rb') as f:
    #     all_courts = list(csv(f))
    # if court_name not in all_courts:
    #     raise ValueError('invalid court_name')

    # Check that data_dir/raw/cases/ exists
    court_data_dir = data_dir + 'raw/' + court_name

    # grab cluster files
    cluster_data_dir = court_data_dir + 'clusters/'
    if not os.path.exists(cluster_data_dir):
        os.makedirs(cluster_data_dir)

    start = time.time()
    download_bulk_resource(court_name, 'clusters', data_dir)
    end = time.time()
    print '%s clusters download took %d seconds' % \
          (court_name, end - start)
    print

    # grab opinion files
    opinion_data_dir = court_data_dir + 'opinions/'
    if not os.path.exists(opinion_data_dir):
        os.makedirs(opinion_data_dir)

    start = time.time()
    download_bulk_resource(court_name, 'opinions', data_dir)
    end = time.time()
    print '%s opinions download took %d seconds' % \
          (court_name, end - start)
    print


def download_bulk_resource(court_name, resource, data_dir):
    """
    Downloads the bulk data files for a given resource from a given court.

    Parameters
    ----------
    court_name: court to download files from

    resource: which resouce to download

    data_dir: relative path to data directory
    """
    if resource not in ['opinions', 'clusters']:
        raise ValueError('invalid resource')

    print 'requesting metadata for %s' % court_name
    court_metadata_url = 'https://www.courtlistener.com/api/rest/v3/%s/?docket__court=%s' % (resource, court_name)
    resource_data_dir = '%sraw/%s/%s/' % (data_dir, court_name, resource)

    # if the directory does not exist then make it
    if not os.path.exists(resource_data_dir):
        os.makedirs(resource_data_dir)

    # check if we already have all cases
    court_metadata = url_to_dict(court_metadata_url)
    num_files_on_server = court_metadata['count']

    files_in_dir = os.listdir(resource_data_dir)
    num_files_in_dir = len(files_in_dir)

    # If the number of files downloaded isn't the
    # same as the number on the server
    if num_files_on_server != num_files_in_dir:
        print 'Downloading %s data for court %s...' % \
                (resource, court_name.upper())

        # Delete the files we currently have
        for filename in files_in_dir:
            os.remove(r'%s/%s' % (resource_data_dir, filename))

        # Download the .tar.gz file
        resource_url = 'https://www.courtlistener.com/api/bulk-data/%s/%s.tar.gz' % (resource, court_name)
        download_url(url=resource_url,
                     path=resource_data_dir)

        # Extract it
        with tarfile.open(resource_data_dir + '%s.tar.gz' % court_name) as tf:
            tf.extractall(path=resource_data_dir)
        # And delete .tar.gz file
        os.remove('%s%s.tar.gz' % (resource_data_dir, court_name))

    else:
        print "All %s %s files accounted for." % (court_name, resource)


def download_master_edgelist(data_dir):
    """
    Downloads the master edgelist

    This is a little jenky -- could probably do this much better without
    writing to disk 7 million times
    """
    url = 'https://www.courtlistener.com/api/bulk-data/citations/all.csv.gz'

    path = data_dir + 'raw/'

    fname_gz = path + 'all.csv.gz'
    fname_csv = path + 'edgelist_master_r.csv'

    print 'downloading edgelist gzip...'
    download_url(url=url,
                 path=path)

    # open gzip
    with gzip.open(fname_gz, 'rb') as f:
        unzipped = f.read()

    # save csv file
    with open(fname_csv, 'w') as f:
        f.write(unzipped)

    # remove .gzip
    os.remove(fname_gz)

    # rename columns
    df = pd.read_csv(fname_csv)
    df.columns = ['citing', 'cited']
    df.to_csv(fname_csv, index=False)


def download_scdb(data_dir):
    # download data from scdb
    scdb_modern_url = 'http://scdb.wustl.edu/_brickFiles/2016_01/SCDB_2016_01_caseCentered_Citation.csv.zip'
    download_zip_to_csv(scdb_modern_url, data_dir + 'scdb/')
    scdb_legacy_url = 'http://scdb.wustl.edu/_brickFiles/Legacy_03/SCDB_Legacy_03_caseCentered_Citation.csv.zip'
    download_zip_to_csv(scdb_legacy_url, data_dir + 'scdb/')


def url_to_dict(url):
    """
    :param url: String representing a json-style object on Court Listener's
    REST API

    :return: html_as_dict, a dictionary of the data on the HTML page
    """
    response = requests.get(url, auth=(username, password))
    html = response.text
    html = html.replace('false', 'False')
    html = html.replace('true', 'True')
    html = html.replace('null', 'None')
    html_as_dict = ast.literal_eval(html)
    return html_as_dict


def download_url(url, path=''):
    """
    This is a quick and easy function that simulates clicking a link in
    your browser that initiates a download.

    url:: the url from which data is to be downloaded.
    path:: the downloaded file to be created.
    """
    filename = path + url.split("/")[-1]

    with open(filename, "wb") as f:
        r = requests.get(url)
        f.write(r.content)


def json_to_dict(path):
    """
    Returns a dictionary version of a json file

    Parameters
    ----------
    path: path to file
    """

    if not os.path.exists(path):
        raise ValueError('file does not exist')

    with open(path) as data_file:
        data = json.load(data_file)
        return data


def download_zip_to_csv(url, path):
    """
    downloads a zipped csv files and unzips it
    The file name is the end of the url
    Assume index_col = 0
    """
    # get the file name and path
    fname = url.split("/")[-1]
    zip_path = path + fname

    # download the zip file
    with open(zip_path, "wb") as f:
        r = requests.get(url)
        f.write(r.content)

    # open the zip file as a csv
    data = pd.read_csv(zip_path)

    # save csv
    data.to_csv(zip_path.split('.zip')[0], index=True)

    # kill the zip file
    os.remove(zip_path)
