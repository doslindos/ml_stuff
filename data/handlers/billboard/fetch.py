from .. import spotify_api_fetch, jsonload, tfdata, split_dataset, rndsample
from collections import Counter
from json import dump as jsondump

class DataFetcher:
    
    def load_data(self, sample=None):
        if not self.save_path.exists():
            json_data = jsonload(self.resource_path.open('r', encoding='utf-8'))
            
            # Create a data dict with key = track id and value = labels
            data = {}
            for key, value in json_data.items():
                if 'Spotify_track_id' in value.keys():
                    track_id = value['Spotify_track_id']
                    #week_ids = value['Week_ids']
                    # Take just year information from the week ids to be used as label
                    #years = []
                    #months = []

                    #for week_id in week_ids:
                    
                    #    month, day, year = week_id.split("/")
                    #    months.append(month)
                        # Because years are from 1958-2019 take only last two digits
                    #    years.append(year[2:])
            
                    if track_id not in data.keys():
                        data[track_id] = 1
            
            # Take a random sample of the full dataset
            if sample is not None:
                new_data = {}
                for key, value in rndsample(data.items(), sample):
                    new_data[key] = value
                data = new_data
            
            spotify_api_fetch(data, self.save_path, crawl_albums=True)
            
        self.dataset = jsonload(self.save_path.open("r", encoding='utf-8'))


    def get_data(self, sample=None):
        # Wrap dataset into tensorflow dataset object
        if sample is not None:
            return rndsample(self.dataset, sample)
        else:
            return self.dataset
        
