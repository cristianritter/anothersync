import configparser
import os.path

ROOT_DIR = os.path.dirname(os.path.abspath(__file__)) # This is your Project Root
CONFIG_PATH = os.path.join(ROOT_DIR, 'config.ini')  
print ("Diretório do arquivo de configurações: ",CONFIG_PATH)
class ConfPacket:
    def __init__(self):
        pass

    def load_config(self, apointed):
        parser = configparser.ConfigParser()

        try:
            parser.read(CONFIG_PATH)
        except Exception as error:
            print ('Erro: ', error)

        if (parser.sections() == []):
            raise NameError("Arquivo config.ini corrompido ou nao encontrado.")
        
        configs = {}
        for item in apointed.split(', ') : 
            configs[item] = {}

            try:
                for key in parser[item]:
                    configs[item][key] = parser[item][key]          
            
            except Exception as error:
                print ('Erro no arquivo config.ini: ', error)
        return configs

def main():
    configs = ConfPacket()
    items = configs.load_config('DEFAULT')
    print(items)

if __name__ == '__main__':
    main()
