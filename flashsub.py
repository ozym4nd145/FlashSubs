import opensubapi
from subdb import SubDBAPI
from imdb import Imdb
import os,sys,string

RUNNING_AS_WINDOW = False

def get_list(dir_path):
	file_list = []
	for direc,fol,files in os.walk(dir_path):
		for fl in files:
			name = os.path.join(direc,fl)
			base_file,ext = os.path.splitext(name)
			if not (os.path.exists(base_file+".srt") and \
				os.path.exists(base_file+".nfo")) and\
				ext in [".avi", ".mp4", ".mkv", ".mpg", ".mpeg", ".mov", ".rm", ".vob", ".wmv", ".flv", ".3gp",".3g2"] and\
				int(os.path.getsize(name)) > 1024*1024*10:
				file_list.append(name)
	return file_list


if __name__ == "__main__":
	try:
		if len(sys.argv) > 1:
			if len(sys.argv) ==2:
				path = sys.argv[1]
				proxy = None
			elif len(sys.argv) > 3:
				print "Usage: {} '<path to directory>' [--proxy=proxy_server_url:port] ".format(sys.argv[0])
				sys.exit()
			elif len(sys.argv) == 3:
				if "--proxy" in sys.argv[1].split('=') :
					proxy = sys.arg[1].split('=')[1]
					path = sys.argv[2]
				elif "--proxy" in sys.argv[2].split('='):
					path = sys.argv[1]
					proxy = sys.argv[2].split('=')[1]
				else:
					print "Usage: {} '<path to directory>' [--proxy=proxy_server_url:port] ".format(sys.argv[0])
					sys.exit()

			if not os.path.isdir(path):
				print "Usage: {} '<path to directory>' [--proxy=proxy_server_url:port] ".format(sys.argv[0])
				sys.exit()
		else:
			RUNNING_AS_WINDOW = True
			path = raw_input("Enter the path of the directory: ")
			if not os.path.isdir(path):
				print "Path given is not valid!"
				sys.exit()
			
			conf = raw_input("Are you working behind a proxy? (y/n): ")
			if conf.lower() in ['y','n',"yes",'yup']:
				proxy = raw_input("Enter proxy_server:port -> ")
			else:
				proxy = None

		subdb = SubDBAPI()
		imdb = Imdb()
		opensub = opensubapi.OpenSubAPI(proxy)
		try:
			token = opensub.login()
			assert type(token)==str
		except:
			print "Login to OpenSubtitles.org failed!"
			sys.exit()
		print "Login Successful"
		#get file list
		movie_list = get_list(path)
		#Total Number of Movies
		num_movie = len(movie_list)
		#subtitle file for movies
		sub_list = [None]*num_movie
		#index number for movies whose imdbid are not yet found
		no_id_index = []
		#imdb id of movies in movie list
		imdb_id_list = [None]*num_movie
		#subtitles id for movies in opensubtitles.org
		open_subs_id = []
		#index for which subs are found in opensubtitles.org
		index_opensub = []
		
		print "Total Files - {}".format(num_movie)

		if num_movie ==0:
			opensub.logout()
			print "No Movie to search subs for!"
			sys.exit()

		#get imdb id for movies whose hash is present in opensubapi
		result = opensub.check_movie_list(movie_list)
		if result:
			for i in xrange(num_movie):
				if result[i]:
					imdb_id_list[i] = result[i]['MovieImdbID']
			
		print "Downloading Subs from Source 1"
		for i in xrange(num_movie):
			if not result[i]:
				print "*",
				movie_hash = subdb.get_hash(movie_list[i])
				if movie_hash == "SizeError":
					continue
				sub = subdb.get_subs(movie_hash,'en')
				if sub:
					sub_list[i] = sub

		#get movies which are present in opensub database by name or hash
		print "\nSearching Subs in Source 2"
		result = opensub.search_sub_list(movie_list)


		len_res = len(result)
		for i in xrange(num_movie):
			if i >= len_res or result[i] == None:
				if not imdb_id_list[i]:
					no_id_index.append(i)
			else:
				if not imdb_id_list[i]:
					imdb_id_list[i] = result[i]['IDMovieImdb']
							
				if not sub_list[i]:
					open_subs_id.append(result[i]['IDSubtitleFile'])
					index_opensub.append(i)
				
		#Download Subs which are found in opensubtitles database
		print "Downloading Subs from Source 2"
		down_subs = {}
		for num in xrange(0,len(open_subs_id),20):
			print "*",
			sub = opensub.download_sub_list(open_subs_id[num:num+20])
			if sub==None:
				for index in xrange(num,num+20):
					temp_sub = opensub.download_sub(open_subs_id[index])
					if temp_sub:
						down_subs.update(temp_sub)
			else:
				down_subs.update(sub)

		for sub_id,index in zip(open_subs_id,index_opensub):
			try:
				down_subs[sub_id]
			except:
				pass
			else:
				sub_list[index] = down_subs[sub_id]

		if len(no_id_index) != 0:
			print "Searching Subs from Source 3"
			no_id_file = []
			for index in no_id_index:
				no_id_file.append(movie_list[index])
			id_list = imdb.get_imdb_id(no_id_file)
			for ids,index in zip(id_list,no_id_index):
				imdb_id_list[index] = ids
			#get info from imdb about movies in movie list
		print "\nGetting Information"
		info_list = imdb.get_info(["tt"+"0"*(7-len(ids))+ids if ids else None for ids in imdb_id_list])

		#Now, sub_list = subtitles for corresponding movies in movie_list
		# info_list = info for correspoding movies in movie_list

		if len(info_list) != len(sub_list) != num_movie:
			print "ERROR"
			sys.exit()

		no_sub_imdb_id = []
		no_sub_imdb_id_index = []

		for i in xrange(num_movie):
			if imdb_id_list[i] != None and sub_list[i] == None:
				no_sub_imdb_id.append(imdb_id_list[i])
				no_sub_imdb_id_index.append(i)

		if len(no_sub_imdb_id) != 0:
			print "Downloading Subs from Source 3"              
			result = opensub.search_sub_list(imdbid_list=no_sub_imdb_id)
			#print result
			sub_id=[]
			sub_id_index=[]
			#Using reversed so that the first MovieHash overwrites the same MovieHashes that come after it.
			result_dict = {res['IDMovieImdb']:res for res in reversed(result)}
			for ids,index in zip(no_sub_imdb_id,no_sub_imdb_id_index):
				try:
					result_dict[ids]
				except:
					pass
				else:
					sub_id_index.append(index)
					sub_id.append(result_dict[ids]['IDSubtitleFile'])
					
			down_sub = opensub.download_sub_list(sub_id)
					
			for ids,index in zip(sub_id,sub_id_index):
				try:
					down_sub[ids]
				except:
					pass
				else:
					sub_list[index] = down_sub[ids]

		#Final - sub_list - subtitles of movies in movie_list
		#Final - info_list - info of movies in movie_list

		print "Writing to Directory"

		#Removing forbidden characters from files (Windows forbidden)
		forbidden_chars = "*.\"/\[]:;|=,'"
		table = string.maketrans(forbidden_chars,' '*len(forbidden_chars))

		for num in xrange(num_movie):
			path = movie_list[num]
			base_path,name = os.path.split(path)
			base_name,ext = os.path.splitext(name)
			info = info_list[num]
			sub = sub_list[num]

			print "Currently Processing - {}".format(path)

			try:
				new_name = info['Title']
			except:
				new_name = base_name
			else:
				if info['Type']=='series':
					continue
				elif info['Type'] == 'episode':
					Season = info['Season']
					Episode = info['Episode']
					if Season.isdigit() and Episode.isdigit():
						len_season = 2
						len_episode = 2
						if len(Episode) > len_episode:
							new_name = "S{0:0>2}E{1}_{2}".format(str(Season),str(Episode),info['Title'])
						else:
							new_name = "S{0:0>2}E{1:0>2}_{2}".format(str(Season),str(Episode),info['Title'])
					else:
						new_name = info['Title']
							
			#So that names do not conflict in Windows ( "/\:|' etc. are not allowed in Windows)
			new_name = str(new_name).translate(table)

			if not os.path.exists(os.path.join(base_path,new_name)+ext):
				os.rename(path,os.path.join(base_path,new_name)+ext)
				print "Renamed {0} to {1}".format(base_name,new_name)
						
				if os.path.exists(os.path.join(base_path,base_name)+".srt"):
					os.rename(os.path.join(base_path,base_name)+".srt",os.path.join(base_path,new_name)+".srt")
				elif sub != None:
					print "Subtitle Added"
					with open(os.path.join(base_path,new_name)+".srt","w") as sub_file:
						sub_file.write(sub)
				if info:
					print "Info Added"
					with open(os.path.join(base_path,new_name)+".nfo","w") as info_file:
						for key in info.keys():
							info_file.write("{0}:\n{1}\n\n".format(key.encode('utf-8'),info[key].encode('utf-8')))
			else:
				if not os.path.exists(os.path.join(base_path,base_name)+".srt") and sub != None:
					print "Subtitle Added"
					with open(os.path.join(base_path,base_name)+".srt","w") as sub_file:
						sub_file.write(sub)
				if info != None and not os.path.exists(os.path.join(base_path,base_name)+".nfo"):
					print "Info Added"
					with open(os.path.join(base_path,base_name)+".nfo","w") as info_file:
						for key in info.keys():
							info_file.write("{0}:\n{1}\n\n".format(key.encode('utf-8'),info[key].encode('utf-8')))


		opensub.logout()
		print("Done!")

		if RUNNING_AS_WINDOW:
			raw_input("Press any key to exit...")
	
	except BaseException as e:
		if not type(e).__name__ == "SystemExit":
			print e
		if RUNNING_AS_WINDOW:
			raw_input("Press any key to exit...")
		sys.exit()
