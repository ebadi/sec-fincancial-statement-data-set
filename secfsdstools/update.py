""" Getting everything ready to work with the data. """
import logging

from secfsdstools._0_config.configmgt import ConfigurationManager, Configuration
from secfsdstools._1_setup.setupdb import DbCreator
from secfsdstools._2_download.secdownloading import SecZipDownloader, UrlDownloader
from secfsdstools._3_index.indexing import ReportZipIndexer

LOGGER = logging.getLogger(__name__)


def update(config: Configuration = None):
    """
    ensures that all available zip files are downloaded and that the index is created.
    """

    # read config
    if config is None:
        LOGGER.info("No configuration provided ... reading configuration file ..")
        config = ConfigurationManager.read_config_file()

    # create the db
    DbCreator(db_dir=config.db_dir).create_db()

    # download actual data
    url_downloader = UrlDownloader(user_agent=config.user_agent_email)
    secdownloader = SecZipDownloader(zip_dir=config.download_dir, urldownloader=url_downloader)
    secdownloader.download()

    # create index of reports
    indexer = ReportZipIndexer(db_dir=config.db_dir, secdownloader=secdownloader)
    indexer.process()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(module)s  %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )

    update(
        Configuration(
            db_dir='c:/ieu/projects/sec-fincancial-statement-data-set/data/db/',
            download_dir='c:/ieu/projects/sec-fincancial-statement-data-set/data/dld/',
            user_agent_email='your.email@goes.here'
        ))
