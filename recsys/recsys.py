#!/usr/bin/env python

""" This file implements a social recommendation system that
assigns your value to an item based on the average of your
friends ratings of that item. This operation corresponds
to a particular matrix-matrix product.  In order to minimize
the output, we only output the top-k recommendations for 
each person, where k is configurable on the command line. """

from mrjob.job import MRJob
import operator

class SocRecSys(MRJob):
    
    def inputmap(self, key, line):
        """Convert the raw input into the data for the recommender.
        
        The input format info is from 
        http://www.trustlet.org/wiki/Epinions_datasets
        
        The rating data is on a line with 8 items:
          ObjId, UserId, Rating, Status, Creation, LastMod, Type, Status
        Rating can be 1-5, Status is 1 if it's visible, 
        The social data is on a line with 4 items:
          MyId, OtherId, Value, Creation
        Value is +-1 for trust/distrust
        All lines are tab-delimited.
        
        We setup a join between trusted users and ratings, as well
        as setup a reduction to count the number of trusted users.
        """
        parts = line.split('\t')
        if len(parts) == 8:
            # rating data
            objid = parts[0].strip()
            uid = parts[1].strip()
            rat = int(parts[2])
            yield (uid, (objid, rat))
        elif len(parts) == 4:
            # user data
            myid = parts[0].strip()
            otherid = parts[1].strip()
            value = int(parts[2])
            if value > 0:
                yield (otherid, (myid,))
        else:
            # should probably throw an error
            pass
            
    def joinred(self, key, vals):
        """Output elements for the matrix-matrix product join.
        
        If the key has length 2, then it's working to count the number
        of people that key trusts.  Otherwise, the key is a user
        trusted by someone else, along with all of their ratings.
        """
        tusers = [] # the user with key is trusted by alluids in tusers
        ratobjs = [] # the articles rated by the user with uid=key
        for val in vals:
            if len(val) == 1:
                tusers.append(val[0])
            else:
                ratobjs.append(val)
        for (objid, rat) in ratobjs:
            for uid in tusers:
                yield ((uid, objid), rat)
                    
    def sumred(self, key, vals):
        s = 0.
        n = 0
        for val in vals:
            s += val
            n += 1
        # the smoothed average of ratings
        yield key, (s+self.options.avg)/float(n+1) 
        
    def rowgroupmap(self, key, val):
        yield key[0], (key[1], val)
    
    def topkoutput(self, key, vals):
        vals = sorted(vals, key=operator.itemgetter(1), reversed=True)
        k = self.options.topk
        recs = []
        for i in xrange(min(k, len(vals))):
            recs.append(vals[i])
        yield key, recs
        
    def configure_options(self):
        super(SocRecSys,self).configure_options()
        self.add_passthrough_option('--avge',default='3',
            dest='avg')
        self.add_passthrough_option('--topk',default=25)
    
    def steps(self):
        return [self.mr(mapper=self.inputmap, reducer=self.joinred),
            self.mr(mapper=None, reducer=self.sumred),
            self.mr(mapper=self.rowgroupmap, reducer=self.topkoutput)]

if __name__=='__main__':
    SocRecSys.run()
