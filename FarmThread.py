from datetime import datetime
from threading import Thread
from time import sleep
from Browser import Browser
import requests

class FarmThread(Thread):
    """
    A thread that creates a capsule farm for a given account
    """

    def __init__(self, log, config, account, stats, locks):
        """
        Initializes the FarmThread

        :param log: Logger object
        :param config: Config object
        :param account: str, account name
        :param stats: Stats, Stats object
        """
        super().__init__()
        self.log = log
        self.config = config
        self.account = account
        self.stats = stats
        self.browser = Browser(self.log, self.config, self.account)
        self.locks = locks

    def run(self):
        """
        Start watching every live match
        """
        try:
            self.stats.updateStatus(self.account, "[green]LOGIN")
            if self.browser.login(self.config.getAccount(self.account)["username"], self.config.getAccount(self.account)["password"], self.locks["refreshLock"]):
                self.stats.updateStatus(self.account, "[green]LIVE")
                self.stats.resetLoginFailed(self.account)
                while True:
                    self.browser.getLiveMatches()
                    dropsAvailable = self.browser.sendWatchToLive()
                    newDrops = []
                    if self.browser.liveMatches:
                        liveMatchesStatus = []
                        for m in self.browser.liveMatches.values():
                            # Color code "drops available"
                            # status = dropsAvailable.get(m.league, False)
                            # if status:
                            #     liveMatchesStatus.append(f"[green]{m.league}[/]")
                            # else: 
                            liveMatchesStatus.append(f"{m.league}")
                        self.log.debug(f"{', '.join(liveMatchesStatus)}")    
                        liveMatchesMsg = f"{', '.join(liveMatchesStatus)}"
                        newDrops = self.browser.checkNewDrops(self.stats.getLastDropCheck(self.account))
                        self.stats.updateLastDropCheck(self.account, int(datetime.now().timestamp()*1e3))
                    else:
                        liveMatchesMsg = "None"
                    self.stats.update(self.account, len(newDrops), liveMatchesMsg)
                    if self.config.connectorDrops:
                        self.__notifyConnectorDrops(newDrops)
                    sleep(Browser.STREAM_WATCH_INTERVAL)
            else:
                self.log.error(f"Login for {self.account} FAILED!")
                self.stats.updateStatus(self.account, "[red]LOGIN FAILED")
                self.stats.addLoginFailed(self.account)
        except Exception:
            self.log.exception(f"Error in {self.account}. The program will try to recover.")

    def stop(self):
        """
        Try to stop gracefully
        """
        self.browser.stopMaintaininingSession()

    def __notifyConnectorDrops(self, newDrops: list):
        if newDrops:
            requests.post(self.config.connectorDrops, json=newDrops)

