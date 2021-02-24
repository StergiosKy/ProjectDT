import csv
import pandas
from sklearn.neighbors import NearestNeighbors
from shutil import copyfile
from collections import Counter
from tkinter import ttk
from tkinter import *
import tkinter.messagebox as mbox
from matplotlib import pyplot as plt
import numpy as np

# global variable that defines from how many neighbours to recommend songs to the user
neighbour_recommendations = 10
# global recommendation variable for the artist recommendations
artist_based_recommendations = 10


# function for the gui
def center(win):
    # centers a tkinter window
    win.update_idletasks()
    width = win.winfo_width()
    frm_width = win.winfo_rootx() - win.winfo_x()
    win_width = width + 2 * frm_width
    height = win.winfo_height()
    titlebar_height = win.winfo_rooty() - win.winfo_y()
    win_height = height + titlebar_height + frm_width
    x = win.winfo_screenwidth() // 2 - win_width // 2
    y = win.winfo_screenheight() // 2 - win_height // 2
    win.geometry('{}x{}+{}+{}'.format(width, height, x, y))
    win.deiconify()


def submit_user():
    user_id = user_combobox.get()
    if not user_id:
        # check if the entry is empty
        mbox.showerror("Song recommendation error", "Please fill in the user id and try again\n")
        return
    else:
        # get the user index
        user_index = users.index(user_id)
        # then proceed to recommend songs to the user
        recommend_song(user_index)


def recommend_song(user):
    # calculate the k nearest neighbours where k = 10 in this case
    neigh = NearestNeighbors(n_neighbors=neighbour_recommendations, metric="precomputed")
    # fit the data
    neigh.fit(user_distance_matrix)
    # find the knn neighbours of the user
    user_neighbours = neigh.kneighbors([user_distance_matrix[user]], return_distance=False)
    # get the average popularity of the songs the user listens to
    total_popularity = 0
    for song in user_song_list[user]:
        total_popularity = total_popularity + popularity[song]
    avg_popularity = total_popularity / len(user_song_list[user])

    song_recommendations = []
    common_songs_per_playlist = []
    user_r_playlists = []
    # begin processing each user that kNN returned
    # we choose to get a song from each neighbours
    for user_r in user_neighbours[0][0:neighbour_recommendations]:
        user_common_songs_per_playlist = []
        # take only the unique playlists
        playlists = dataframe[dataframe['user_id'] == users[user_r]]['playlist'].unique().tolist()
        # append the playlist for future usage
        user_r_playlists.append(playlists)
        for playlist in playlists:
            user_r_songs = dataframe[(dataframe['user_id'] == users[user_r]) & (dataframe['playlist'] == playlist)]['artist_name'].str.cat(dataframe[(dataframe['user_id'] == users[user_r]) & (dataframe['playlist'] == playlist)]['song_title'], sep=" , ").tolist()
            # get the length of the intersection of all the songs of the "to recommend" user with the songs
            # of each playlist of the recommender user
            common_playlist_songs = len(set(user_song_list[user]).intersection(user_r_songs))
            # append the data
            user_common_songs_per_playlist.append(common_playlist_songs)
        # append the counts for future usage
        common_songs_per_playlist.append(user_common_songs_per_playlist)
    # find the closest playlist of each user_r to the user, save the indices
    closest_playlists = []
    for c_list in common_songs_per_playlist:
        max_value = max(c_list)
        max_index = c_list.index(max_value)
        closest_playlists.append(max_index)
    # now start the recommendation process
    # for user i
    for i in range(len(closest_playlists)):
        # select the playlist and its songs
        playlist_songs = dataframe[(dataframe['user_id'] == users[user_neighbours[0][i]]) & (dataframe['playlist'] == user_r_playlists[i][closest_playlists[i]])]['artist_name'].str.cat(dataframe[(dataframe['user_id'] == users[user_neighbours[0][i]]) & (dataframe['playlist'] == user_r_playlists[i][closest_playlists[i]])]['song_title'], sep=" , ").tolist()
        # choose the first song and compare with the rest
        best_song = playlist_songs[0]
        pos = 0
        # safety flag
        dodge_flag = 0
        # make sure the user has not listened it it before
        while best_song in user_song_list[user]:
            if (pos+1) >= len(playlist_songs):
                # index out of range
                dodge_flag = 1
                break
            pos = pos + 1
            best_song = playlist_songs[pos]
        min_song_distance = abs(popularity[best_song] - avg_popularity)
        # compare with the rest
        for j in range(pos+1, len(playlist_songs)):
            if abs(popularity[playlist_songs[j]] - avg_popularity) < min_song_distance:
                # if the user has already heard it, then skip it
                if playlist_songs[j] in user_song_list[user]:
                    break
                # if it has already been recommended, also skip it
                elif playlist_songs[j] in song_recommendations:
                    break
                min_song_distance = abs(popularity[playlist_songs[j]] - avg_popularity)
                best_song = playlist_songs[j]
        song_recommendations.append(best_song)
        # cleanup if need be
        # if the dodge flag is set, it means this is a garbage value and needs to be removed
        if dodge_flag:
            song_recommendations.pop()

    # second pair of recommendations
    # this is based solely on new songs of the same artists
    # and then using the popularity to choose from the artist's songs
    second_recommendations = []
    for user_r in user_neighbours[0][0:artist_based_recommendations]:
        # select only the common artist songs
        common_artists = set(user_artist_list[user]).intersection(user_artist_list[user_r])
        artist_songs = dataframe[dataframe['artist_name'].isin(common_artists)]['artist_name'].str.cat(dataframe[dataframe['artist_name'].isin(common_artists)]['song_title'], sep=" , ").tolist()
        # do the following only if we actually find songs
        if len(artist_songs) > 0:
            best_song = artist_songs[0]
            # same logic as earlier
            pos = 0
            # safety flag
            dodge_flag = 0
            while best_song in user_song_list[user]:
                if (pos+1) >= len(artist_songs):
                    # index out of range case
                    dodge_flag = 1
                    break
                pos = pos + 1
                best_song = artist_songs[pos]
            min_song_distance = abs(popularity[best_song] - avg_popularity)
            # compare with the rest
            for j in range(pos+1, len(artist_songs)):
                if abs(popularity[artist_songs[j]] - avg_popularity) < min_song_distance:
                    # if the user has already heard it, then skip it
                    if artist_songs[j] in user_song_list[user]:
                        break
                    # if it has already been recommended, also skip it
                    elif artist_songs[j] in second_recommendations:
                        break
                    min_song_distance = abs(popularity[artist_songs[j]] - avg_popularity)
                    best_song = artist_songs[j]
            second_recommendations.append(best_song)
            # same thing as before
            if dodge_flag:
                second_recommendations.pop()

    # cleanup the second list as it may have duplicate values
    # this will result in less recommendations but it is necessary
    second_recommendations = list(dict.fromkeys(second_recommendations))

    # create a window to display the data
    window.withdraw()
    recommendation_window = Toplevel()
    recommendation_window.configure(background='black')
    recommendation_window.geometry('1000x600')
    recommendation_window.title('Recommendations')
    recommendation_window.resizable(width=False, height=False)
    center(recommendation_window)

    user_label_2 = Label(recommendation_window, text='USER RECOMMENDATIONS', font=("Impact", 20), bg="SpringGreen2", fg="black")
    user_label_2.grid(row=1, column=1, columnspan=3, sticky='ew')

    # songs
    recommendation_label = Label(recommendation_window, text='POPULARITY BASED SONG RECOMMENDATION', font=("Impact", 20), bg="SpringGreen2", fg="black")
    recommendation_label.grid(row=2, column=1, columnspan=3, sticky='ew')
    # sort for better appearance at the gui
    song_recommendations.sort()
    rec_songs_combobox = ttk.Combobox(recommendation_window, state='readonly', font=('Calibri', 12), values=song_recommendations)
    rec_songs_combobox.grid(row=3, column=1, columnspan=3, sticky='wen')

    rec_as_combobox_label = Label(recommendation_window, text='ARTIST BASED SONG RECOMMENDATION', font=("Impact", 20), bg="SpringGreen2", fg="black")
    rec_as_combobox_label.grid(row=5, column=1, columnspan=3, sticky='ew')
    # sort for better appearance at the gui
    second_recommendations.sort()
    rec_as_combobox = ttk.Combobox(recommendation_window, state='readonly', font=('Calibri', 12), values=second_recommendations)
    rec_as_combobox.grid(row=6, column=1, columnspan=3, sticky='wen')

    rec_combobox_label = Label(recommendation_window, text='USER\'S PREVIOUS SONGS', font=("Impact", 20), bg="SpringGreen2", fg="black")
    rec_combobox_label.grid(row=8, column=1, columnspan=3, sticky='ew')
    # sort for better appearance at the gui
    user_song_list[user].sort()
    rec_combobox = ttk.Combobox(recommendation_window, state='readonly', font=('Calibri', 12), values=user_song_list[user])
    rec_combobox.grid(row=9, column=1, columnspan=3, sticky='wen')

    return_button = Button(recommendation_window, text='EXIT', font=('Impact', 20), fg='black', bg='SpringGreen2',
                        command=lambda: return_back(recommendation_window))
    return_button.grid(row=11, column=3)

    # row/column weights for spacing
    recommendation_window.columnconfigure(0, weight=1)
    recommendation_window.columnconfigure(4, weight=1)
    recommendation_window.rowconfigure(0, weight=1)
    recommendation_window.rowconfigure(1, weight=1)
    recommendation_window.rowconfigure(4, weight=1)
    recommendation_window.rowconfigure(7, weight=1)
    recommendation_window.rowconfigure(10, weight=1)
    recommendation_window.rowconfigure(11, weight=1)


def return_back(recommendation_window):
    recommendation_window.destroy()
    window.deiconify()


def plot_data():
    # plot the data for the 10 most common
    most_popular_songs = popularity.most_common(10)
    artists = dataframe['artist_name']
    artist_popularity = Counter(artists)
    most_popular_artists = artist_popularity.most_common(10)

    # convert the data to lists
    artist_popularity1 = []
    artist_popularity2 = []
    most_popular_songs1 = []
    most_popular_songs2 = []
    for x, y in most_popular_songs:
        most_popular_songs1.append(x)
        most_popular_songs2.append(y)
    for x, y in most_popular_artists:
        artist_popularity1.append(x)
        artist_popularity2.append(y)

    # start plotting
    plt.figure(1)
    fig1 = plt.bar(np.arange(len(most_popular_songs2)), height=most_popular_songs2)
    plt.title('Song Popularity of the Dataset')
    plt.xticks(np.arange(len(most_popular_songs1)), most_popular_songs1, rotation=90)
    plt.ylabel('Song Popularity')
    plt.draw()

    plt.figure(2)
    fig2 = plt.bar(np.arange(len(artist_popularity2)), height=artist_popularity2)
    plt.title('Artist Popularity of the Dataset')
    plt.xticks(np.arange(len(artist_popularity1)), artist_popularity1, rotation=90)
    plt.ylabel('Artist Popularity')
    plt.draw()

    # show the plots
    plt.show()


# driver code
csv_file = "spotify_dataset.csv"
csv_file_2 = "spotify_dataset_2.csv"

# clean up the dataset using regex
copyfile(csv_file, csv_file_2)

file = open(csv_file, 'r', encoding="utf-8").read()
file_2 = re.sub(r'^"', '', file, flags=re.MULTILINE)
# remove trailing semicolons
file_2 = re.sub(r'";+', '"', file_2)

file_3 = open(csv_file_2, 'w', encoding="utf-8")
file_3.write(file_2)
file_3.close()

# read the data of onto a data frame
dataframe = pandas.read_csv(csv_file_2, header=[0], encoding='utf-8', quotechar='"', doublequote=True, quoting=csv.QUOTE_ALL, error_bad_lines=False)
dataframe = dataframe.replace(r'"+', '', regex=True)
dataframe.columns = ["user_id", "artist_name", "song_title", "playlist"]
# get the unique user id and song title lists
users = dataframe['user_id'].unique().tolist()
# this has both songs and artists as songs can have duplicate names but not artists
unique_songs = dataframe['artist_name'].str.cat(dataframe['song_title'], sep=" , ").unique().tolist()

# calculate the song popularity
songs = dataframe['artist_name'].str.cat(dataframe['song_title'], sep=" , ").tolist()
popularity = Counter(songs)

# distance matrix pre-processing
song_distance_matrix = []
local_list = []

# pre-allocate the columns
user_artist_list = [None] * len(users)
user_song_list = [None] * len(users)

for i in range(len(users)):
    # get a copy of only the artists per user
    user_artist_list[i] = dataframe[dataframe['user_id'] == users[i]]['artist_name'].unique().tolist()
    # get a copy of a list of artist + song per user
    user_song_list[i] = dataframe[dataframe['user_id'] == users[i]]['artist_name'].str.cat(
        dataframe[dataframe['user_id'] == users[i]]['song_title'], sep=" , ").tolist()

# preallocate the distance matrix, the diagonal already has it's final value set
user_distance_matrix = []
for i in range(len(users)):
    user_distance_matrix.append([1000000] * len(users))

# build the distance matrix
for i in range(len(users)):
    for j in range(i+1, len(users)):
        common_artists = len(set(user_artist_list[i]).intersection(user_artist_list[j]))
        common_songs = len(set(user_song_list[i]).intersection(user_song_list[j]))
        # the distance of the users is the inverse of their similarity in music taste
        # since kn neighbours does not accept float values from numpy
        # we decided to use a safe enough big number and subtract from that the current metric we have
        user_distance_matrix[i][j] = user_distance_matrix[j][i] = user_distance_matrix[j][i] - (100 * common_artists + 50*common_songs)

# generate a window and configure it properly
window = Tk()
window.configure(background='black')
window.geometry('800x600')
window.title('Recommendation menu')
window.resizable(width=False, height=False)
center(window)

app_label = Label(window, text='SONG RECOMMENDATION APP', font=("Impact", 20), bg="SpringGreen2", fg="black")
app_label.grid(row=0, column=1, columnspan=3, sticky='ew')
user_label = Label(window, text='USER', font=("Impact", 20), bg="SpringGreen2", fg="black")
user_label.grid(row=1, column=1, columnspan=3, sticky='ew')
user_combobox = ttk.Combobox(window, state='readonly', font=('Calibri', 12), values=users)
user_combobox.grid(row=2, column=1, columnspan=3, sticky='we')

exit_button = Button(window, text='EXIT', font=('Impact', 20), fg='black', bg='SpringGreen2', command=lambda: window.destroy())
exit_button.grid(row=4, column=3)
recommend_button = Button(window, text='RECOMMEND', font=('Impact', 20), fg='black', bg='SpringGreen2', command=lambda: submit_user())
recommend_button.grid(row=4, column=2)
plot_button = Button(window, text='SHOW PLOTS', font=('Impact', 20), fg='black', bg='SpringGreen2', command=lambda: plot_data())
plot_button.grid(row=4, column=1)

# row/column weights for spacing
window.columnconfigure(0, weight=1)
window.columnconfigure(4, weight=1)
window.columnconfigure(2, weight=1)
window.rowconfigure(0, weight=1)
window.rowconfigure(3, weight=1)
window.rowconfigure(4, weight=1)
window.mainloop()
