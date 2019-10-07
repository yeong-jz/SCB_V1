## Load packages
# Load packages
import re
import json
import pickle
import string
import requests
import numpy as np
import pandas as pd
from os import listdir, makedirs
from   bs4    import BeautifulSoup
from datetime import datetime, date
from os.path import isfile, join,exists
from  urllib.request import Request,urlopen
from helper_func import promo_caption_analysis
from completion import *
from google_api_caller import *
pd.set_option('display.max_columns', 999)
import time

start_time = time.time()

class Extract:
    def get_cards(self):
        pass
    def get_promotions(self):
        pass
    def get_card_promotions(self):
        pass
    def get_url_content(self,url):
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        webpage = urlopen(req).read()
        return webpage
    
class ScbExtract(Extract):
    """ Get the card name """
    def get_cards(self, url):
        webpage = self.get_url_content(url)
        souptxt = BeautifulSoup(webpage,'lxml')
        cards = pd.DataFrame()
        productcontents = souptxt.find_all("li",attrs={"class":"item card has-desc"})
        for productcontent in productcontents:
            productname = (productcontent.find("h3", attrs={"class":"title"}).get_text()).strip()
            productdesc = (productcontent.find("p", attrs={"class":"description"}).get_text()).strip()            
            for EachPart in productcontent.select('a[class*="front is-link"]'):
                producthref = EachPart.get('href')                
            row = pd.DataFrame([productname, productdesc, producthref]).T
            cards = pd.concat([cards,row])
        return cards
    """ Get the promotion code """
    def GetPromoCode(self, text, patternlist):
        patterns = "|".join(patternlist)
        srcresult = [ i for i in text.split("\n") if not re.findall(patterns,i.upper())==[]]
        pattern=[re.findall(patterns,k.upper()) for k in srcresult]
        pattern = list(set([y for x in pattern for y in x]))
        if len(pattern)>0:
            pattern = pattern[0]
            srcresult = [(s.upper().split(pattern)[-1]).strip().split()[0] for s in srcresult]
            for puncs in ["â€.",":",";",'"',"'",",",")","]","}","(","[","{"]:
#                print('bef = ',srcresult)
                srcresult = [i.replace(puncs, '') for i in srcresult if len(i)>2]
#                print('aft = ',srcresult)
            #srcresult = srcresult[0]
        return srcresult
    """ Get the image """
    def get_image(self, img_url, img_set, dir_path, img_name):
        try:
            img_path = dir_path+ img_name + re.findall(r'(\.jpg|\.jpeg|\.png)', img_url)[0]
        except:
            img_path = dir_path+ img_name + '.jpg'
        if img_name not in img_set:
#             img_res = requests.get(img_url)
#             with open(img_path, 'wb') as handle:
#                 handle.write(img_res.content)
            img_set.add(img_name)
        return img_path
    """ Get the compressed merchant name """
    def compress(self, name):
        name = name.translate(str.maketrans('', '', string.punctuation))
        name = ''.join([i if ord(i) < 128 else ' ' for i in name])
        name="".join(name.lower().split())
        return name

    """ Get the minimum pax """
    def GetMinPax(self, text, patternlist):
        patterns = "|".join(patternlist)
        ret = re.findall(patterns,text)
        if len(ret):
            ret = [int(s) for s in ret[0] if s.isdigit()][0]
        else:
            ret = np.NaN
        return ret
    """ Get the maximum pax """
    def GetMaxPax(self, text, patternlist):
        patterns = "|".join(patternlist)
        ret = re.findall(patterns,text)
        if len(ret):
            ret = [int(s) for s in ret[0] if s.isdigit()][0]
        else:
            ret = np.NaN
        return ret
    """ Get the sentence """
    def GetSentence(self,text):
        sentences=[]
        if len(re.findall("\n",text))>1:
            para = re.split(r'\n', text.strip())
            for line in para:
                sublines = re.split(r' *[\.\?!][\'"\)\]]* *', line.strip())
                for subline in sublines:
                    if len(subline)>0:
                        sentences += [subline] 
        return sentences
    """ Get the image deprecated """
    def get_image_deprecated(self,img_url,img_set, dir_path, img_name):
        img_path=np.NaN
        if len(img_url)>0:
            img_name = img_url.split('/')[-1]
            if not re.search(r'\.(jpg|jpeg|png)$', img_name):
                img_name = img_name.split("\\")[0]
                if not re.search(r'\.(jpg|jpeg|png)$', img_name):
                    img_name = img_name.split('?')[0]
            img_path = dir_path+ img_name
            if img_name not in img_set:
                img_res = requests.get(img_url)
                with open(img_path, 'wb') as handle:
                    handle.write(img_res.content)
                img_set.add(img_name)         
        return img_path
    """ Get the set of image's name """
    def set_imgurl_fname(self,url,setname):
        urlcontainer = "/".join(url.split("/")[0:-1])
        ext = (url.split("/")[-1]).split(".")[-1]
        fname = "".join(url.split("/")[-1].split(".")[0:-1]).strip()
        return urlcontainer+"/"+setname+"."+ext
    """ Get the issuer exclusivity """
    def get_issuer_exclusivity(self,terms):
        dictkeys = {'visa':'visa', 'master':'mastercard|master card', 'amex':'americanexpress|american express', 'unionpay':'unionpay|union pay'}
        issuer_count = {'visa':0, 'master':0,'amex':0,'unionpay':0}
        for key,value in dictkeys.items():
            issuer_count[key] = len(re.findall(value, terms.lower()))
        if max(issuer_count.values())==0:
            return 'all'
        else:
            return  max(issuer_count, key=issuer_count.get)
    """ Get the postal code """
    def GetPostalCode(self,address):
        IsSingapore = True if len(re.findall('Singapore', address)) else False
        pc = ""
        if IsSingapore:
            pc = address.split("Singapore")[-1].strip()
        return pc
    """ Get the exclusion rule """
    def get_exclusionrule(self,offr):
        visa = [offr["visa"]] if ("visa" in offr)  else [False]
        master = [offr["mas"]] if ("mas" in offr)  else [False]
        exclusion ="scb_all"
        if ((visa[0]) & (not master[0])):
            exclusion ="scb_visa"
        if((not visa[0]) & (master[0])):
            exclusion ="scb_master"
        return exclusion
    """ Get the promotions"""
    def get_promotions(self, url):
        json_data = self.get_url_content(url).decode('utf-8')
        d     = json.loads(json_data)
        rows  = []
        count = 0
        columns=["promo_code","minmaxlimit","card_name","id", "merchant_name","promotion_caption","promotion","image_url","start", "end","terms","category","subcategory","visa","master",'website',"raw_input","vcardlist","mcardlist","brcode","qrcode",'storename','address',"latitude","longitude","ophr","phone","fax"]
        for offr in d['offers']['offer']:
            vcardlist=offr['visa_card_list'] if ('visa_card_list' in offr) else []            
            mcardlist=offr['master_card_list'] if ('master_card_list' in offr) else []            
            vallen = len(mcardlist)
            row=[]
            vTerm=BeautifulSoup(offr["tnc"],'lxml').getText().strip()
            promocaption = offr["otitle"].strip()
            promotioncontainer =BeautifulSoup(offr["odesc"],'lxml')
            promotion = promotioncontainer.getText().strip()
            ## Figuring out Exclusivity ##        
            listitems = promotioncontainer.find("ul")
            promocode = []
            minspend = []

            if(len(promocode)==0):
                for sentence in self.GetSentence(promotion):
                    if len(re.findall('promo code',sentence.lower()))>0 and len(re.findall('does not apply|is not applicable|terms and conditions',sentence.lower()))==0 :
                        promocode+=[sentence]
            if(len(promocode)==0):
                for sentence in self.GetSentence(vTerm):
                    if len(re.findall('promo code',sentence.lower()))>0 and len(re.findall('does not apply|is not applicable|terms and conditions',sentence.lower()))==0 :
                        promocode+=[sentence]

            if(len(promocode)>0):
                promocode =list(np.unique(np.array(promocode)))
                prmcode =[]
                for prm in promocode:
                    prm=re.sub(' +', ' ', prm.strip()) 
                    if len(re.findall('promo code',prm.lower()))>0 and len(re.findall('does not apply|is not applicable|terms and conditions',prm.lower()))==0 :
                        prmcode.append(prm)
                promocode = ". ".join(prmcode)
            else:
                promocode = ""
                    
            if(len(minspend)==0):
                for sentence in self.GetSentence(vTerm):
                    if len(re.findall("limited to|limited of upto|minimum spend|maximum|min\.\s\d*",sentence.lower()))>0 and len(re.findall('goods and service|terms of service|reserves the right|not limited to|is not applicable|terms and conditions',sentence.lower()))==0 :
                        minspend+=[sentence]

            if(len(minspend)>0):
                minspend =list(np.unique(np.array(minspend)))
                prmcode =[]
                for prm in minspend:
                    prm=re.sub(' +', ' ', prm.strip())
                    if len(re.findall("limited to|limited of upto|minimum spend|maximum|min\.\s\d*",prm.lower()))>0 and len(re.findall('goods and service|terms of service|reserves the right|not limited to|is not applicable|terms and conditions',prm.lower()))==0 :
                        prmcode.append(prm)
                minspend = ". ".join(prmcode)
            else:
                minspend = ""
                        
            if len(promocaption)==0:
                promocaption = re.split(r'\n', promotion)[0]
            row+=[promocode]
            row+=[minspend]
            row+=[self.get_exclusionrule(offr)]
            row+=[offr["id"]]
            row+=[offr["name"].strip()]
            
            row+=[promocaption]
            row+=[promotion]
            row+=[offr["oimg"].strip()]
            sd=datetime.strptime(offr["sd"].strip(), "%d-%m-%Y %H:%M:%S").date()            
            row+=[sd]            
            ed=datetime.strptime(offr["ed"].strip(), "%d-%m-%Y %H:%M:%S").date()            
            row+=[ed]            
            row+=[vTerm]
            row+= [offr["cat"]] if ("cat" in offr)  else [""]
            row+=[offr["sbcat"]] if ("sbcat" in offr)  else [""]
            row+=[offr["visa"]]  if ("visa" in offr)  else [False]
            row+=[offr["mas"]] if ("mas" in offr)  else [False]
            row+=[offr["url"]]
            row+=[offr]
            row+=[str(vcardlist)]
            row+=[str(mcardlist)]
            row+=[offr["brcode"]]
            row+=[offr["qrcode"]]

            if len(offr['venue'])>0:
                cnt=0
                OfferVenue = offr['venue']              
                for venue in OfferVenue:
                    mrow=[]
                    for k,v in venue.items():
                        v=str(v).strip() if (k in venue) else "" 
                        v= "" if v == "None" else v
                        v=re.sub("/","|",v)
                        mrow.append(v)
                    rows.append(row+mrow)
                    cnt+=1
            else:
                mrow=['','','','','','','']
                rows.append(row+mrow)              
            count+=1
        deals = pd.DataFrame(rows, columns=columns)        
        return deals
    """ Get the card promotions """
    def get_card_promotions(self, outfile, promotions, cards):
        pass  
# main
if  __name__  ==  '__main__' :   
    deals_url  = "https://www.sc.com/sg/data/tgl/offers.json"
    cc_link    = "https://www.sc.com/sg/credit-cards/"
    scb_obj    = ScbExtract()
    SCBDeals   = scb_obj.get_promotions(deals_url)
    SCBDeals['flag']=""
    SCBDeals['comments']=""
    SCBDeals['postal_code'] = SCBDeals.address.apply(scb_obj.GetPostalCode)
    SCBDeals.phone=SCBDeals.phone.apply(lambda x:(''.join(x.strip().split(" "))).split("Ext:")[0])
    cc         = scb_obj.get_cards(cc_link)
    cc.columns = ['card_name','feature','linktofeaturedetails']
    cc.to_csv("scb_cards.csv")
    SCBDeals['issuer_exclusivity']     = SCBDeals.terms.apply(lambda x:scb_obj.get_issuer_exclusivity(x))
    SCBDeals['merchant_compressed']    = SCBDeals.merchant_name.apply(scb_obj.compress)
    
    img_dir='images/scb/' + str(date.today()) + '/'
    if not exists(img_dir):
        makedirs(img_dir)
    img_set = set([f for f in listdir(img_dir) if isfile(join(img_dir, f))])
    SCBDeals["image_path"]             = SCBDeals[["image_url","merchant_compressed"]].apply(lambda x:scb_obj.get_image(x[0],img_set,img_dir,x[1]),axis=1)
    
    #-------------------------------------------------------------------------------------------
    # Derive is_online
    #-------------------------------------------------------------------------------------------
    SCBDeals['is_online']              = SCBDeals.category.apply(lambda x: x.lower()=="online")

    #-------------------------------------------------------------------------------------------
    # Handling of min_pax, max_pax
    #-------------------------------------------------------------------------------------------
    patternlist=["min\. of \d diners","minimum of \d diners","min\. of \d pax","minimum of \d pax","min\. of \d person","minimum of \d person","min\. of \d people","minimum of \d people"]
    SCBDeals['min_pax']                = SCBDeals.terms.apply(lambda x:scb_obj.GetMinPax(x,patternlist))
    patternlist=["max. of \d pax","maximum of \d pax","max. of \d diners","maximum of \d diners","max. of \d person","maximum of \d person","max. of \d people","maximum of \d people"]
    SCBDeals['max_pax']                = SCBDeals.terms.apply(lambda x:scb_obj.GetMaxPax(x,patternlist))

    #-------------------------------------------------------------------------------------------
    # Handling of promo codes
    #-------------------------------------------------------------------------------------------
    print("Handling promo codes")
    patternlist                     = ['PROMO CODE:','PROMO CODE :','PROMO CODE']
    SCBDeals['promo_code']          = SCBDeals.promotion.apply(lambda x: scb_obj.GetPromoCode(x,patternlist))
    xpromorows                      = SCBDeals[SCBDeals.promo_code.apply(len)==0]
    xpromorows.promo_code           = ""
    promorows                       = SCBDeals[SCBDeals.promo_code.apply(len)>0]

    promorow                        = pd.DataFrame()
    for index, row in promorows.iterrows():
        crow = row.copy()
        for i in row.promo_code:
            crow.promo_code=str(i)
            promorow = pd.concat([promorow,pd.DataFrame(crow).T]) 
    SCBDeals   = pd.concat([xpromorows,promorow])
    
    data_folder = "data/"

    """ Load merchant_dict """
    with open(data_folder + 'merchant_dict_clean.pickle', 'rb') as handle:
        merchant_dict = pickle.load(handle)

    """ Load cat_to_stdcat  for CC cat """
    with open(data_folder + 'cat_to_CC_cat.pickle', 'rb') as handle:
        cat_to_CCcat = pickle.load(handle)
    """ Load stdcategory_to_googletype  for CC cat """
    with open(data_folder + 'CC_category_to_googletype.pickle', 'rb') as handle:
        CCcategory_to_googletype = pickle.load(handle)
    """ Load std_category_taxonomy  for CC cat """
    with open(data_folder + 'CC_category_taxonomy.pickle', 'rb') as handle:
        CC_category_taxonomy = pickle.load(handle)

    """ Load cat_to_stdcat """
    with open(data_folder + 'cat_to_stdcat.pickle', 'rb') as handle:
        cat_to_stdcat = pickle.load(handle)
    """ Load stdcategory_to_googletype """
    with open(data_folder + 'stdcategory_to_googletype.pickle', 'rb') as handle:
        stdcategory_to_googletype = pickle.load(handle)
    """ Load std_category_taxonomy """
    with open(data_folder + 'std_category_taxonomy.pickle', 'rb') as handle:
        std_category_taxonomy = pickle.load(handle)

    postal_code_map = pd.read_csv(data_folder + 'RegionTable.csv')

    #-------------------------------------------------------------------------------------------
    # Handling of promotion analytic
    #-------------------------------------------------------------------------------------------
    
    SCBDeals['promotion_analytic']  = SCBDeals.promotion_caption.apply(lambda x: promo_caption_analysis(x))

    #-------------------------------------------------------------------------------------------
    # Handling of standarlization
    #-------------------------------------------------------------------------------------------
    SCBDeals.category          = SCBDeals.category.apply(lambda x: np.nan if str(x)=="" else x)
    SCBDeals.subcategory       = SCBDeals.subcategory.apply(lambda x: np.nan if str(x)=="" else x)
    SCBDeals['google_api']     = SCBDeals[['address', 'is_online']].apply(lambda x: completion_google_api(x.address, x.is_online)[0], axis=1)
    SCBDeals['listing_outlet'] = SCBDeals[['address', 'is_online']].apply(lambda x: completion_google_api(x.address, x.is_online)[1], axis=1)
    SCBDeals['std_category']   = SCBDeals[['card_name', 'category', 'subcategory', 'merchant_name', 'promotion', 'terms']].apply(lambda x: 
            completion_stdcat(str(x.card_name), str(x.category), str(x.subcategory), str(x.merchant_name), 
                              str(x.promotion), str(x.terms), cat_to_stdcat, std_category_taxonomy)[1], axis=1)
    SCBDeals['cc_buddy_category'] = SCBDeals[['card_name', 'category', 'subcategory', 'merchant_name', 'promotion', 'terms']].apply(lambda x: 
                completion_CCcat(str(x.card_name), str(x.category), str(x.subcategory), str(x.merchant_name), 
                                 str(x.promotion), str(x.terms), cat_to_CCcat, CC_category_taxonomy), axis=1)   
    SCBDeals['google_type'] = SCBDeals.std_category.apply(lambda x: completion_google_type(x, stdcategory_to_googletype)) 

    #-------------------------------------------------------------------------------------------
    # Handling of postal code
    #-------------------------------------------------------------------------------------------
    SCBDeals['postal_code']      = SCBDeals[['is_online', 'postal_code']].apply(lambda x: str(completion_postal(x.is_online, x.postal_code, postal_code_map)[0]), axis=1)
    SCBDeals['country']          = SCBDeals['postal_code'].apply(lambda x: "SGP")
    SCBDeals['sector']           = SCBDeals[['is_online', 'postal_code']].apply(lambda x: str(completion_postal(x.is_online, x.postal_code, postal_code_map)[1]), axis=1)
    SCBDeals['district']         = SCBDeals[['is_online', 'postal_code']].apply(lambda x: str(completion_postal(x.is_online, x.postal_code, postal_code_map)[2]), axis=1)
    SCBDeals['district_name']    = SCBDeals[['is_online', 'postal_code']].apply(lambda x: str(completion_postal(x.is_online, x.postal_code, postal_code_map)[3]), axis=1)
    SCBDeals['general_location'] = SCBDeals[['is_online', 'postal_code']].apply(lambda x: str(completion_postal(x.is_online, x.postal_code, postal_code_map)[4]), axis=1) 
    SCBDeals['area']             = SCBDeals[['is_online', 'postal_code']].apply(lambda x: str(completion_postal(x.is_online, x.postal_code, postal_code_map)[5]), axis=1) 

    ############################################################################################
    print("Output data")
    ColStandard                     = ['card_name', 'category', 'subcategory', 'cc_buddy_category', 'std_category', 'merchant_name', 
                                       'merchant_compressed', 'google_type', 'promotion', 'promotion_caption','promotion_analytic', 'promo_code', 'address', 
                                       'latitude', 'longitude', 'start', 'end', 'phone', 'website', 'image_url', 'image_path', 'issuer_exclusivity', 
                                       'raw_input','min_pax','max_pax', 'is_online', 'listing_outlet', 'google_api', 'terms', 'postal_code', 'country',
                                       'sector', 'district', 'district_name', 'general_location', 'area', 'flag', 'comments']   
    StandardDeals=SCBDeals[ColStandard]
    StandardDeals.to_csv("scb_" + str(date.today()) +".csv",index=False)
    
    print("$$$$$$$$$$$$$$$$$ OUTPUT SUCCESS $$$$$$$$$$$$$$$$$$$$")
    print("------------ %s minutes ------------" %((time.time() - start_time)/60))
    
    
