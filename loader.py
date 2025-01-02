import time
import requests
import os
from utils.file_manager import FileManager


class HashiCorpLoader:
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

    def __obtain_api_token(self):
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
            "audience": "https://api.hashicorp.cloud"
        }

        response = requests.post(url=self.api_token_url, headers=headers, data=data)

        if response.status_code == 200:
            return response.json().get("access_token")
        raise RuntimeError("Hashicorp secret loading was failed")

    def __init__(
        self,
        dump_env_to_file: bool = False,
        folder_to_save_env_dump: str = None,
    ):
        """
        param dump_to_env_file: bool - if True, remote secrets will also be dumped .env.dump file
        param folder_to_save_dump: str - path to the folder where .env.dump file will be saved
        """
        self.client_id: str = os.environ.get('HCP_CLIENT_ID')
        self.client_secret: str = os.environ.get('HCP_CLIENT_SECRET')
        self.api_token_url: str = os.environ.get('HCP_API_TOKEN_URL')
        self.secrets_url: str = os.environ.get('HCP_SECRETS_URL')

        if not all((self.client_id, self.client_secret, self.api_token_url, self.secrets_url)):
            raise RuntimeError(
                "HCP_CLIENT_ID, HCP_CLIENT_SECRET, HCP_API_TOKEN_URL, HCP_SECRETS_URL must be set in env"
            )

        # set dump settings
        self.dump_env_to_file = dump_env_to_file
        self.folder_to_save_dump = folder_to_save_env_dump

        self.__api_token = self.__obtain_api_token()

    def __retrieve_remote_secrets(self) -> list[dict]:
        response = requests.get(self.secrets_url, headers={"Authorization": f"Bearer {self.__api_token}"})

        try:
            return response.json()['secrets']
        except Exception as e:
            raise RuntimeError(f"Error occurred while retrieving data from Hashcorp vault: {str(e)}")

    def load(self):
        """
        This method loads HashiCorp secrets to environment variables.
        """
        if not os.environ.get('hcp_loaded'):
            if self.dump_env_to_file:
                dump_file = os.path.join(self.folder_to_save_dump, '.env.dump')

                os.makedirs(os.path.dirname(self.folder_to_save_dump), exist_ok=True)

                if not os.path.exists(self.folder_to_save_dump):
                    os.makedirs(self.folder_to_save_dump)

                open(dump_file, "w").close() # creating/overwriting the file

                secrets_for_dump = dict()

            # retrieving secrets
            remote_secrets: list[dict] = self.__retrieve_remote_secrets()

            # loading to env

            for secret_pair in remote_secrets:
                k, v = secret_pair['name'], secret_pair['static_version']['value']
                os.environ[k] = v

                if self.dump_env_to_file:
                    secrets_for_dump[k] = v

            first = True
            if self.dump_env_to_file:
                for k, v in secrets_for_dump.items():
                    if first:
                        FileManager.append(file_path=dump_file, content=f"{k}={v}")
                        first = False
                    else:
                        FileManager.append(file_path=dump_file, content=f"\n{k}={v}")
                time.sleep(2)  # waiting to write the file

            # setting env_loaded to any value to indicate it has already been loaded
            os.environ['hcp_loaded'] = '1'

            print("HashiCorp secrets are successfully loaded to environment!")
        else:
            print("HashiCorp secrets were already loaded. Skipping...")
