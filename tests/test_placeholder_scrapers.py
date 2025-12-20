from jobspy.dice import Dice
from jobspy.wellfound import Wellfound
from jobspy.remoteok import RemoteOK
from jobspy.weworkremotely import WeWorkRemotely
from jobspy.remoterocketship import RemoteRocketship
from jobspy.model import ScraperInput


def test_placeholder_scrapers_return_jobresponse():
    si = ScraperInput(site_type=[])
    for cls in (Dice, Wellfound, RemoteOK, WeWorkRemotely, RemoteRocketship):
        inst = cls()
        res = inst.scrape(si)
        assert hasattr(res, "jobs")
        assert isinstance(res.jobs, list)
