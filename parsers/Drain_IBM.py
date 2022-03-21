from CONSTANTS import *
from drain3 import TemplateMiner
from drain3.file_persistence import FilePersistence
from drain3.template_miner_config import TemplateMinerConfig

# Dispose Loggers.
DrainLogger = logging.getLogger('drain')
DrainLogger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler(sys.stderr)
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - " + SESSION + " - %(levelname)s: %(message)s"))

file_handler = logging.FileHandler(os.path.join(LOG_ROOT, 'drain.log'))
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - " + SESSION + " - %(levelname)s: %(message)s"))

DrainLogger.addHandler(console_handler)
DrainLogger.addHandler(file_handler)
DrainLogger.info(
    'Construct DrainLogger success, current working directory: %s, logs will be written in %s' %
    (os.getcwd(), LOG_ROOT))


class Drain3Parser():
    def __init__(self, config_file, persistence_folder):
        self.config = TemplateMinerConfig()
        if not os.path.exists(config_file):
            DrainLogger.info('No configuration file specified, use default values for Drain.')
        else:
            DrainLogger.info('Load Drain configuration from %s' % config_file)
            self.config.load(config_file)
        self.config.profiling_enabled = False
        persistence_folder = os.path.join(persistence_folder, 'ibm_drain_depth-' + str(self.config.drain_depth) \
                                          + '_st-' + str(self.config.drain_sim_th))
        self.persistence_folder = persistence_folder
        if not os.path.exists(persistence_folder):
            DrainLogger.warning('Persistence folder does not exist, creating one.')
            os.makedirs(persistence_folder)
        persistence_file = os.path.join(persistence_folder, 'persistence')
        DrainLogger.info('Searching for target persistence file %s' % persistence_file)
        persistence_file = os.path.join(persistence_folder, persistence_file)
        fp = FilePersistence(persistence_file)
        self.parser = TemplateMiner(persistence_handler=fp, config=self.config)
        self.load('File', persistence_file)

    def parse_file(self, in_file, remove_cols=None, clean=False,encode='utf-8'):
        DrainLogger.info('Start parsing input file %s' % in_file)
        with open(in_file, 'r', encoding=encode) as reader:
            if remove_cols:
                DrainLogger.info('Removing columns: [%s]' % (' '.join([str(x) for x in remove_cols])))
            for line in tqdm(reader.readlines()):
                line = line.strip()
                # In case some of the columns are useless.
                if remove_cols:
                    line = self.remove_columns(line, remove_cols, clean=clean)
                self.parser.add_log_message(line)
        self.parser.save_state('Finish parsing.')
        with open(os.path.join(self.persistence_folder, 'templates.txt'), 'w', encoding='utf-8') as writer:
            for cluster in self.parser.drain.clusters:
                writer.write(str(cluster) + '\n')
        DrainLogger.info('Parsing file finished.')
        return self.parser.drain.clusters

    def remove_columns(self, line, remove_cols, clean=False):
        tokens = line.split()
        after_remove = []
        for i, token in enumerate(tokens):
            if i not in remove_cols:
                after_remove.append(token)
        line = ' '.join(after_remove)
        return line if not clean else re.sub('[\*\.\?\+\$\^\[\]\(\)\{\}\|\\\/]', '', ' '.join(after_remove))

    def parse_line(self, in_line, remove_cols=None, save_right_after=False):
        line = in_line.strip()
        if remove_cols:
            line = self.remove_columns(line, remove_cols)
        self.parser.add_log_message(line)
        if save_right_after: self.parser.save_state('Saving as required')
        return self.parser.drain.clusters

    def match(self, inline):
        return self.parser.match(inline)

    def load(self, type, input):
        if type == 'File':
            if not os.path.exists(input):
                DrainLogger.info('Persistence file %s not found, please train a new one.' % input)
                self.to_update = True
            else:
                DrainLogger.info('Persistence file found, loading.')
                self.to_update = False
                fp = FilePersistence(input)
                self.parser = TemplateMiner(config=self.config, persistence_handler=fp)
                self.parser.load_state()
                DrainLogger.info('Loaded.')
            pass
        else:
            DrainLogger.error('We are currently not supporting other types of persistence.')
            raise NotImplementedError


if __name__ == '__main__':
    DrainLogger.info('Testing program start.')
    remove_cols = [0, 1, 2, 3, 4]
    parser = Drain3Parser(config_file=os.path.join(PROJECT_ROOT, 'conf/HDFS.ini'),
                          persistence_folder=os.path.join(PROJECT_ROOT, 'datasets/HDFS/persistences'))

    input_file = os.path.join(PROJECT_ROOT, 'datasets/HDFS/HDFS.log')

    if parser.to_update:
        # learn log events from raw log.
        DrainLogger.info('Start training a new parser.')
        if not os.path.exists(input_file):
            DrainLogger.error('File %s not found. Please check the dataset folder' % input_file)
            exit(1)
        parser.parse_file(in_file=input_file, remove_cols=remove_cols)

    pass
