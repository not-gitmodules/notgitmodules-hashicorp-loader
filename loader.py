import time
import requests
import os
from typing import Union


class LoaderHelpers:
    @staticmethod
    def _obtain_api_token(client_id, client_secret, api_token_url):
        """Obtains the API token from HashiCorp"""
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
            "audience": "https://api.hashicorp.cloud"
        }

        response = requests.post(url=api_token_url, headers=headers, data=data)

        if response.status_code == 200:
            return response.json().get("access_token")
        raise RuntimeError("Hashicorp secret loading was failed")

    @staticmethod
    def _fetch_remote_secrets(secrets_url, api_token):
        """Fetches secrets from Hashicorp"""
        response = requests.get(secrets_url, headers={"Authorization": f"Bearer {api_token}"})

        try:
            return response.json()['secrets']
        except Exception as e:
            raise RuntimeError(f"Error occurred while retrieving data from Hashcorp vault: {str(e)}")

    @staticmethod
    def _prepare_dump(folder_to_save_dump: str) -> str:
        dump_file = os.path.join(folder_to_save_dump, '.env.dump')

        os.makedirs(os.path.dirname(folder_to_save_dump), exist_ok=True)

        if not os.path.exists(folder_to_save_dump):
            os.makedirs(folder_to_save_dump)

        open(dump_file, "w").close()  # creating/overwriting the file
        return dump_file


class HashiCorpLoader(LoaderHelpers):
    """
    To use this class you need to set the following environment variables:
        HCP_CLIENT_ID
        HCP_CLIENT_SECRET
        HCP_API_TOKEN_URL
        HCP_SECRETS_URL

    Yes, it's meant, to already have a HashiCorp credentials set in your environment!
    Docs: https://www.vaultproject.io/api-docs/secret/kv/kv-v2#list-secrets

    HashiCorpLoader works:
        1. You obtain API token from server with your client id and client secret
        2. Then you retrieve your secrets using the obtained API token

    It's a stateless class designed to retrieve data without keeping it.
    It optionally can dump secrets to .env.dump file.
    """

    def __init__(
        self,
        folder_to_save_dump: str = None,
        save_dump: bool = True,
    ):
        """
        param dump_to_env_file: bool - if True, remote secrets will also be dumped .env.dump file
        param folder_to_save_dump: str - path to the folder where .env.dump file will be saved
        """
        if save_dump:
            assert isinstance(folder_to_save_dump, str), f"folder_to_save_dump be a path, not {folder_to_save_dump}!"

        self.client_id: str = os.environ.get('HCP_CLIENT_ID')
        self.client_secret: str = os.environ.get('HCP_CLIENT_SECRET')
        self.api_token_url: str = os.environ.get('HCP_API_TOKEN_URL')
        self.secrets_url: str = os.environ.get('HCP_SECRETS_URL')

        if not all((self.client_id, self.client_secret, self.api_token_url, self.secrets_url)):
            raise RuntimeError(
                "HCP_CLIENT_ID, HCP_CLIENT_SECRET, HCP_API_TOKEN_URL, HCP_SECRETS_URL must be set in env"
            )

        # set dump settings
        self.save_dump = save_dump
        self.folder_to_save_dump = folder_to_save_dump

        self.__api_token = self._obtain_api_token(client_id=self.client_id, client_secret=self.client_secret,
                                                  api_token_url=self.api_token_url)

    def load(self, debug: bool = False) -> Union[None, dict]:
        """
        This method loads HashiCorp secrets to environment variables.

        If debug is none, means

        """
        if not os.environ.get('hcp_loaded'):
            # retrieving secrets
            response: list[dict] = self._fetch_remote_secrets(secrets_url=self.secrets_url, api_token=self.__api_token)
            remote_secrets = {secret_pair['name']: secret_pair['static_version']['value'] for secret_pair in response}

            # loading to env
            for k, v in remote_secrets.items():
                os.environ[k] = v

            # .env.dump file
            if self.save_dump:
                dump_file: str = self._prepare_dump(folder_to_save_dump=self.folder_to_save_dump)

                with open(dump_file, "a") as f:
                    for i, (k, v) in enumerate(remote_secrets.items()):  # first break-line stuff
                        f.write(f"{k}={v}") if i == 0 else f.write(f"\n{k}={v}")
                time.sleep(2)  # waiting to write the file

            # setting env_loaded to any value to indicate it has already been loaded
            os.environ['hcp_loaded'] = '1'

            print("HashiCorp secrets are successfully loaded to environment!")

            if debug:
                return response

        else:
            print("HashiCorp secrets were already loaded. Skipping...")
