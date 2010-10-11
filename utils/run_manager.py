import sys
import subprocess
import time
import re

class TrackValidation:
    '''
    Class for deciding whether a track summary from a run should be
    considered valid based on the overheads and response times recorded
    '''
    def __init__(self, trackname):
        self.track_name = trackname
        self.pct_overhead_ops = 0.0
        self.pct_overhead_ops_acceptable = False
        self.pct_ops_failed = 0.0
        self.pct_failed_ops_acceptable = False
        self.op_response_time_targets_met = True

    def is_acceptable(self):
        return self.pct_overhead_ops_acceptable and \
            self.pct_failed_ops_acceptable and \
            self.op_response_time_targets_met

class TrackSummary:
    '''
    Class for storing the summary results of a load track
    '''
    def __init__(self, trackname):
        self.name = trackname
        self.offered_load_ops_per_sec = 0
        self.effective_load_ops_per_sec = 0
        self.littles_estimate_ops_per_sec = 0
        self.effective_load_reqs_per_sec = 0
        self.operations_successful = 0
        self.operations_failed = 0
        self.average_op_response_time_sec = 0
        self.average_users = 0
        self.op_response_time_targets_met = True
    
    def validate( self, pct_overhead_ops=5.0, pct_failed_ops=5.0 ):
        result = TrackValidation(self.name)
        # check overheads
        
        if self.littles_estimate_ops_per_sec > 0:
            result.pct_overhead_ops = \
                ((self.littles_estimate_ops_per_sec - \
                      self.effective_load_ops_per_sec)/\
                     self.littles_estimate_ops_per_sec)*100.0

            if result.pct_overhead_ops <= pct_overhead_ops:
                result.pct_overhead_ops_acceptable = True
        else:
            result.pct_overhead_ops_acceptable = False

        total_ops = self.operations_successful + self.operations_failed
        result.pct_ops_failed = \
            (float(self.operations_failed)/float(total_ops))*100.0
        
        if result.pct_ops_failed <= pct_failed_ops:
            result.pct_failed_ops_acceptable = True

        return result

    def __repr__(self):
        '''
        Craft our own string representation
        '''
        # Validate ourselves first
        # Construct the string with our results
        # callers can print this out, write it to a file, etc.
        validation = self.validate()                                 
                
        return RainOutputParser.RESULTS_DATA.format(\
            self.name, \
            self.effective_load_ops_per_sec, \
            self.littles_estimate_ops_per_sec,\
            self.effective_load_reqs_per_sec, \
            validation.pct_overhead_ops, \
            self.average_op_response_time_sec, \
            self.average_users, \
            self.operations_successful, \
            self.operations_failed, \
            validation.pct_ops_failed, \
            str(validation.is_acceptable()) )

class RainOutputParser:
    '''
    Class for parsing the output from Rain. Returns a list of track summaries
    '''
    RESULTS_HEADER = "{0:<20} {1:<10s} {2:<10s} {3:<10s} {4:<10s} {5:<10s} "\
                "{6:<10s} {7:<10s} {8:<10s} {9:<10s} {10:<5s}".format(\
                "track",\
                "eff-ops/s",\
                "ltl-ops/s",\
                "eff-reqs/s",\
                "%ovh-ops",\
                "avg-resp(s)",\
                "avg-users",\
                "succeeded",\
                "failed",\
                "%failed",\
                "passed" )
    RESULTS_DATA = "{0:<20} {1:10.4f} {2:10.4f} {3:10.4f} {4:10.4f} {5:10.4f}"\
                   "{6:10.4f} {7:10} {8:10} {9:10.4f} {10:<5s}"


    @staticmethod
    def parse_output( output ):
        '''
        Parse the output for each track and return a list with summary results
        for each track
        '''
        #print output
        # Find all the track names
        track_results = []
        track_pattern = re.compile( '\[TRACK: (.*)\] starting load scheduler' )
        tracks = track_pattern.findall( output )
       
        # for each track go get some numbers from the final results section
        for track in tracks:
            #print track
            # sub-pattern of the end of a result line from rain
            # <metric><space*>:<space+><decimal value>
            result_line_tail_pattern = \
                '\s*:\s+([-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)'
            track_final_results_pattern = \
              re.compile( '\[SCOREBOARD TRACK: ' + track + '\] Final results' )
            track_offered_load_ops_pattern = \
                re.compile( '\[SCOREBOARD TRACK: ' + track + '\] ' \
                       'Offered load \(ops/sec\)' + result_line_tail_pattern )
            track_effective_load_ops_pattern = \
                re.compile( '\[SCOREBOARD TRACK: ' + track + '\] ' \
                      'Effective load \(ops/sec\)' + result_line_tail_pattern )
            track_littles_estimate_ops_pattern = \
              re.compile( '\[SCOREBOARD TRACK: ' + track + '\] ' \
              'Little\'s Law Estimate \(ops/sec\)' + result_line_tail_pattern )
            track_effective_load_reqs_pattern = \
                re.compile( '\[SCOREBOARD TRACK: ' + track + '\] ' \
                'Effective load \(requests/sec\)' + result_line_tail_pattern )
            track_ops_successful_pattern = \
               re.compile( '\[SCOREBOARD TRACK: ' + track + '\] ' \
               'Operations successfully completed' + result_line_tail_pattern )
            track_ops_failed_pattern = \
               re.compile( '\[SCOREBOARD TRACK: ' + track + '\] ' \
                           'Operations failed' + result_line_tail_pattern )
            track_avg_op_response_time_pattern = \
             re.compile( '\[SCOREBOARD TRACK: ' + track + '\] ' \
                         'Average operation response time \(s\)' + \
                             result_line_tail_pattern )
            track_avg_users_pattern = \
                re.compile( '\[SCOREBOARD TRACK: ' + track + '\] ' \
                      'Average number of users' + result_line_tail_pattern )

            # Create a new track summary instance to fill in
            summary = TrackSummary(track)
            # Find the "Final results" marker for this track and then
            # search for individual metrics
            match = track_final_results_pattern.search( output )
            if match:
                # search the substring from the final results marker 
                # for more specific stuff after this point
                final_results_section_start = match.start()
                summary.offered_load_ops_per_sec = \
                    float( track_offered_load_ops_pattern.search\
                             ( output, final_results_section_start ).group(1) )
                summary.effective_load_ops_per_sec = \
                    float( track_effective_load_ops_pattern.search\
                             ( output, final_results_section_start ).group(1) )
                summary.littles_estimate_ops_per_sec = \
                    float( track_littles_estimate_ops_pattern.search\
                             ( output, final_results_section_start ).group(1) )
                summary.effective_load_reqs_per_sec = \
                    float( track_effective_load_reqs_pattern.search\
                             ( output, final_results_section_start ).group(1) )
                summary.operations_successful = \
                    long( track_ops_successful_pattern.search\
                             ( output, final_results_section_start ).group(1) )
                summary.operations_failed = \
                    long( track_ops_failed_pattern.search\
                             ( output, final_results_section_start ).group(1) )
                summary.average_op_response_time_sec = \
                    float( track_avg_op_response_time_pattern.search\
                             ( output, final_results_section_start ).group(1) )
                summary.average_users = \
                    float( track_avg_users_pattern.search\
                             ( output, final_results_section_start ).group(1) )
                
                # save the summary to the list we have so far
                track_results.append(summary)
        
        # return the list of track results we found
        return track_results

    @staticmethod
    def print_results( results, output_stream=sys.stdout ):
        output_stream.write( RainOutputParser.RESULTS_HEADER + '\n' )
        for result in results:
            output_stream.write( str(result) + '\n' )
        # Flush the output stream
        output_stream.flush()


class RunManager():
    """
    A class for launching runs and validating results.
    """
    @staticmethod
    def run_rain( config_file="config/rain.config.ac.json", \
                  classpath=".:rain.jar:workloads/httptest.jar", \
                  min_heapsize="-Xms256m", \
                  max_heapsize="-Xmx1g", \
                  gc_policy="-XX:+DisableExplicitGC" ):
        """
        Launch process for Rain, get pid and then start querying
        sched stats
        """
        args = ["java", min_heapsize, max_heapsize, gc_policy, \
            "-cp", classpath, "radlab.rain.Benchmark", config_file  ]
        
        rain_process = None
        rain_process = subprocess.Popen(args, bufsize=-1, \
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        rain_pid = rain_process.pid
        print( "[Run manager] rain pid: %d" % rain_pid )
        
        # Sit and wait until Rain exits then parse the output
        retcode = rain_process.poll()
        if retcode == None:
            print( "[Run manager] Rain running..." )
        else: 
            print( "[Run manager] Rain process failed to start. Retcode: {0}"\
                       .format(retcode) )
            sys.exit(2)

        interrupted = False
        check_interval = 30

        while retcode == None:
            #try:
            print "[Run Manager] sleeping for {0} secs".format(check_interval)
            time.sleep(check_interval)
            print "[Run manager] woken...checking on driver process..."
            retcode = rain_process.poll()
            if retcode == None:
                print "[Run manager] Rain process still running..."
            else:
                print "[Run manager] Rain process exited. Retcode: {0}"\
                    .format(retcode)

        # Return the raw output, clients can parse it themselves 
        # or use the RainOutputParser to make sense
        # of it
        output = rain_process.stdout.read()
        return output

'''
Example command line
java -Xms256m -Xmx1g -XX:+DisableExplicitGC -cp .:rain.jar:workloads/httptest.jar radlab.rain.Benchmark config/rain.config.ac.json
'''

def run2():
    try:
        results_file = open( "./rain.out", 'r' )
        results = results_file.read()
        track_results = RainOutputParser.parse_output( results )
        RainOutputParser.print_results( track_results )
    #except:
    #    print "something broke"
    finally:
        if not results_file.closed:
            results_file.close()

def run3():
    
    config_file = "config/rain.config.ac.json"
    classpath = ".:rain.jar:workloads/httptest.jar"    
    output = RunManager.run_rain(config_file, classpath)
    track_results = RainOutputParser.parse_output( output )                
    RainOutputParser.print_results( track_results, sys.stdout )           
    #return track_results 

if __name__=='__main__':
      run3()
