#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'venues'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120), nullable=False)
    image_link = db.Column(db.String(500), default='')
    facebook_link = db.Column(db.String(120), default='')
    # extra columns added
    genres = db.Column(db.String(120), default='')
    website = db.Column(db.String(120), default='')
    seeking_talent = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.String(500), default='')
    shows = db.relationship("Show", backref="venue", lazy="joined")

    def __repr__(self):
      return f'<Venue id:{self.id}> name:{self.name}>'


class Artist(db.Model):
    __tablename__ = 'artists'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120), nullable=False)
    genres = db.Column(db.String(120), default='')
    image_link = db.Column(db.String(500), default='')
    facebook_link = db.Column(db.String(120), default='')
    # extra columns added
    website = db.Column(db.String(120), default='')
    seeking_venue = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.String(500), default='')
    shows = db.relationship("Show", backref="artist", lazy=True)

    def __repr__(self):
      return f'<Artist id:{self.id}> name:{self.name}>'
    

class Show(db.Model):
  __tablename__ = 'shows'

  id = db.Column(db.Integer, primary_key=True)
  venue_id = db.Column(db.Integer, db.ForeignKey('venues.id'))
  artist_id = db.Column(db.Integer, db.ForeignKey('artists.id'))
  start_time = db.Column(db.DateTime, nullable=False)


  def __repr__(self):
      return f'<Show id:{self.id} venue_id:{self.venue_id} artist_id:{self.artist_id}>'


#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale="en")

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  # get distinct venue locations
  locations =  Venue.query.with_entities(Venue.city, Venue.state).distinct(Venue.state).all()

  result = []
  for location in locations:
    city, state = location

    venues = Venue.query.filter(Venue.city == city, Venue.state == state).all()
    
    result_venues = []
    for venue in venues:
      result_venues.append({'id': venue.id, 'name': venue.name, 'num_upcoming_shows': len(checkFutureShows(venue.shows))})

    result.append({'city': city, 'state': state, 'venues': result_venues})

  return render_template('pages/venues.html', areas=result);

@app.route('/venues/search', methods=['POST'])
def search_venues():
  search_term = request.form['search_term']
  search_result = Venue.query.filter(Venue.name.ilike(f'%{search_term}%')).all()
  response = {
    "count": len(search_result),
    "data": [{'id': venue.id, 'name': venue.name, 'num_upcoming_shows': len(checkFutureShows(venue.shows)) } for venue in search_result]
  }
  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  current_venue = Venue.query.get(venue_id)

  data = {
    'id': current_venue.id,
    'name': current_venue.name ,
    'genres': current_venue.genres.replace('{', '').replace('}', '').split(','),
    'address': current_venue.address,
    'city': current_venue.city,
    'state': current_venue.state,
    'phone': current_venue.phone,
    'website': current_venue.website,
    'facebook_link': current_venue.facebook_link,
    'seeking_talent': current_venue.seeking_talent,
    'seeking_description': current_venue.seeking_description,
    'image_link': current_venue.image_link,
  }

  past_shows, future_shows = [], []
  for show in current_venue.shows:
    artist_at_show = db.session.query(Artist.id, Artist.name, Artist.image_link).filter_by(id = show.artist_id).first()

    artist_data = {'artist_id': artist_at_show.id, 
            'artist_name': artist_at_show.name, 
            'artist_image_link': artist_at_show.image_link,
            'start_time': str(show.start_time)}

    if show.start_time > datetime.now():
      future_shows.append(artist_data)
    else:
      past_shows.append(artist_data)

  # adding past and future show into data object
  data['past_shows'] = past_shows
  data['past_shows_count'] = len(past_shows)
  data['upcoming_shows'] = future_shows
  data['upcoming_shows_count'] = len(future_shows)
  
  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  try:
    new_venue = Venue(name = request.form['name'],
                  genres = request.form.getlist('genres'),
                  address = request.form['address'],
                  city = request.form['city'],
                  state = request.form['state'],
                  phone = request.form['phone'],
                  facebook_link = request.form['facebook_link'])
    db.session.add(new_venue)
    db.session.commit()
    flash('Venue ' + request.form['name'] + ' was successfully listed!')

  except Exception as e:
    db.session.rollback()
    flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')

  finally:
    db.session.close()

  return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  try:
    venue = Venue.query.get(venue_id)
    name = venue.name
    db.session.delete(venue)
    db.session.commit()
    flash('Venue ' + name + ' was successfully deleted!')

  except Exception as e:
    print(e)
    db.session.rollback()
    flash('Venue couldn\'t be deleted.')

  finally:
    db.session.close()
    redirect('/', code=302)

  return {}



#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  data = []
  artists = Artist.query.with_entities(Artist.id, Artist.name).all()
  
  for artist in artists:
    data.append({'id': artist.id, 'name': artist.name})

  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  search_term = request.form['search_term']
  search_result = Artist.query.filter(Artist.name.ilike(f'%{search_term}%')).all()
  response = {
    "count": len(search_result),
    "data": [{'id': artist.id, 'name': artist.name, 'num_upcoming_shows': len(checkFutureShows(artist.shows)) } for artist in search_result]
  }
  
  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  current_artist = Artist.query.get(artist_id)
  data = {
      'id': artist_id,
      'name': current_artist.name,
      'genres': current_artist.genres.replace('{', '').replace('}', '').split(','),
      'city': current_artist.city,
      'state': current_artist.state,
      'phone': current_artist.phone,
      'website': current_artist.website,
      'facebook_link': current_artist.facebook_link,
      'seeking_venue': current_artist.seeking_venue,
      'seeking_description': current_artist.seeking_description,
      'image_link': current_artist.image_link
    }

  past_shows, future_shows = [], []
  for show in current_artist.shows:
    show_venue = db.session.query(Venue.id, Venue.name, Venue.image_link).filter_by(id = show.artist_id).first()

    artist_data = {'venue_id': show_venue.id, 
            'venue_name': show_venue.name, 
            'venue_image_link': show_venue.image_link,
            'start_time': str(show.start_time)}

    if show.start_time > datetime.now():
      future_shows.append(artist_data)
    else:
      past_shows.append(artist_data)
    
    # adding past and future show into data object
    data['past_shows'] = past_shows
    data['past_shows_count'] = len(past_shows)
    data['upcoming_shows'] = future_shows
    data['upcoming_shows_count'] = len(future_shows)
  
  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistForm()

  current_artist = Artist.query.get(artist_id)

  artist = {
    "id": artist_id,
    "name": current_artist.name,
    "genres": current_artist.genres,
    "city": current_artist.city,
    "state": current_artist.state,
    "phone": current_artist.phone,
    "website": current_artist.website,
    "facebook_link": current_artist.facebook_link,
    "seeking_venue": current_artist.seeking_venue,
    "seeking_description":  current_artist.seeking_description,
    "image_link":  current_artist.image_link,
  }

  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  try:
    current_artist = Artist.query.get(artist_id)
    current_artist.name = request.form['name']
    current_artist.genres = request.form.getlist('genres')
    current_artist.city = request.form['city']
    current_artist.state = request.form['state']
    current_artist.phone = request.form['phone']
    current_artist.facebook_link = request.form['facebook_link']
    db.session.commit()
    flash('Artist ' + request.form['name'] + ' was successfully updated!')

  except Exception as e:
    db.session.rollback()
    flash('An error occurred. Artist ' + request.form['name'] + ' could not be updated.')

  finally:
    db.session.close()

  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm()

  current_venue = Venue.query.get(venue_id)

  venue = {
    "id": venue_id,
    "name": current_venue.name,
    "genres": current_venue.genres,
    "address": current_venue.address,
    "city": current_venue.city,
    "state": current_venue.state,
    "phone": current_venue.phone,
    "website": current_venue.website,
    "facebook_link": current_venue.facebook_link,
    "seeking_talent": current_venue.seeking_talent,
    "seeking_description":  current_venue.seeking_description,
    "image_link":  current_venue.image_link,
  }

  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  try:
    current_venue = Venue.query.get(venue_id)
    current_venue.name = request.form['name'],
    current_venue.genres = request.form.getlist('genres')
    current_venue.address = request.form['address']
    current_venue.city = request.form['city']
    current_venue.state = request.form['state']
    current_venue.phone = request.form['phone']
    current_venue.facebook_link = request.form['facebook_link']
    db.session.commit()
    flash('Venue ' + request.form['name'] + ' was successfully updated!')

  except Exception as e:
    db.session.rollback()
    flash('An error occurred. Venue ' + request.form['name'] + ' could not be updated.')

  finally:
    db.session.close()

  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  try:
    new_artist = Artist(name = request.form['name'],
                  genres = request.form.getlist('genres'),
                  city = request.form['city'],
                  state = request.form['state'],
                  phone = request.form['phone'],
                  facebook_link = request.form['facebook_link'])
    db.session.add(new_artist)
    db.session.commit()
    flash('Artist ' + request.form['name'] + ' was successfully listed!')

  except Exception as e:
    db.session.rollback()
    flash('An error occurred. Artist ' + data.name + ' could not be listed.')

  finally:
    db.session.close()

  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  shows = Show.query.all()
  data = []
  for show in shows:
    result = {
      "venue_id": show.venue_id,
      "artist_id": show.artist_id,
      "start_time": str(show.start_time),
      "venue_name": show.venue.name,
      "artist_name": show.artist.name,
      "artist_image_link": show.artist.image_link,
    }
    data.append(result)

  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  try:
    new_show = Show(artist_id = request.form['artist_id'],
    venue_id = request.form['venue_id'],
    start_time = request.form['start_time'])
    db.session.add(new_show)
    db.session.commit()
    flash('Show was successfully listed!')

  except:
    db.session.rollback()
    flash('An error occurred. Show could not be listed.')

  finally:
    db.session.close()

  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Utils function.
#----------------------------------------------------------------------------#

def checkFutureShows(shows):
    future_shows = []
    for show in shows:
        if show.start_time > datetime.now():
            future_shows.append(show)
    return future_shows

def checkPastShows(shows):
    past_shows = []
    for show in shows:
        if show.start_time <= datetime.now():
            past_shows.append(show)
    return past_shows
#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
