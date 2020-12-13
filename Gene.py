import pandas as pd

class Gene:
    def __init__(self, units):
        self.weight_gene1 = []
        self.bias_gene1 = []
        self.weight_gene2 = []
        self.bias_gene2 = []
        self.num_units = units

        self.weight_gene1 = RandomGenerator.getRandomArray(units[0] * units[1])
        self.bias_gene1 = RandomGenerator.getRandomArray(units[1])
        self.weight_gene2 = RandomGenerator.getRandomArray(units[1] * units[2])
        self.bias_gene2 = RandomGenerator.getRandomArray(units[2])
    
    def readWeigth(self, file_name):
        df = pd.read_csv(file_name)
        self.num_units = [int(df.iloc[0]), int(df.iloc[1]), int(df.iloc[2])]
        start_ind = list(df['units'] == 'bias1').index(True)
        end_ind = list(df['units'] == 'weight1').index(True)
        self.bias_gene1 =np.array(df['units'].iloc[start_ind+1:end_ind]).astype('float64')
        start_ind = list(df['units'] == 'weight1').index(True)
        end_ind = list(df['units'] == 'bias2').index(True)
        self.weight_gene1 = np.array(df['units'].iloc[start_ind+1:end_ind]).astype('float64')
        start_ind = list(df['units'] == 'bias2').index(True)
        end_ind = list(df['units'] == 'weight2').index(True)
        self.bias_gene2 = np.array(df['units'].iloc[start_ind+1:end_ind]).astype('float64')
        start_ind = list(df['units'] == 'weight2').index(True)
        self.weight_gene2 = np.array(df['units'].iloc[start_ind+1:]).astype('float64')
        print('Read Gene Weight.')
