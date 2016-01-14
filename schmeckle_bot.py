# Find comments with schmeckles in it and comment with value converted to USD
import praw
import re
import locale
import collections
import os

import auth_config

#########################################################
# Setup

# For converting from string numbers with english-based commas to floats
locale.setlocale(locale.LC_ALL, 'eng_USA') # Windows
# locale.setlocale(locale.LC_ALL, 'en_US') # Linux

# Set up praw
schmeckle_bot_name = "SchmeckleBot"
user_agent = schmeckle_bot_name + " converts Schmeckles to USD in rickandmorty subreddit. See https://github.com/Elucidation/schmeckle_bot"

# Login
r = praw.Reddit(user_agent=user_agent)

# Login old-style due to Reddit politics
r.login(auth_config.USERNAME, auth_config.PASSWORD, disable_warning=True)

# Get accessor to comments
subreddit = r.get_subreddit('rickandmorty')
comments = subreddit.get_comments(limit=None)

# Look for '<number> schmeckle' ignore case (schmeckles accepted implicitly)
# Works for positive negative floats, but fails softly on EXP
p = re.compile('(-?[\d|,]*\.{0,1}\d+ schmeckle[\w]*)', re.IGNORECASE)

# Ignore quotes
quote_remove = re.compile("^> .*\n", re.MULTILINE)

# How long a quote in either direction can be before truncating
max_sentence_buffer = 100

#########################################################
# Helper Functions

def getQuote(body):
  """Generate Quote for comment"""
  lines = []
  body = quote_remove.sub('', body) # Remove quoted lines

  if len(body) > max_sentence_buffer*2:
    for match in p.finditer(body):
      short_line = ""
      a = max(0,match.start()-max_sentence_buffer)
      b = min(len(body),match.end()+max_sentence_buffer)
      short_line = body[a:b]

      if a == 0:
        s_a = ''
      else:
        s_a = '...'
      if b == len(body):
        s_b = ''
      else:
        s_b = '...'

      lines.append(s_a+short_line+s_b)
  else:
    lines = [body]
  
  quote = ["> " + p.sub(r'**\1**', line) + "\n" for line in lines]
  return quote

def schmeckle2usd(schmeckle):
  """1 Schmeckle = $148 USD
  https://www.reddit.com/r/IAmA/comments/202owt/we_are_dan_harmon_and_justin_roiland_creators_of/cfzfv79"""
  return schmeckle * 148.0

def getConversion(body):
  """Calculate schmeckle to USD responses"""
  values = []
  msg_template = u"* {:,.2f} Schmeckles → **${:,.2f} USD**\n"
  pairs = p.findall(body)
  if len(pairs) > 0:
    for match in pairs:
      # '<number> schmeckle' -> match, float(<number>)
      values.append(locale.atof(match.split()[0]))

  response = [msg_template.format(schmeckle, schmeckle2usd(schmeckle)) for schmeckle in values]
  return [response, values]

def getResponse(body):
  """Get response packet to use for replying to message"""
  # If there is a schmeckle value in body
  if p.search(body):
    quote = getQuote(body)
    conversion, values = getConversion(body)

    # Combine into message
    msg = "\n\n".join(quote)
    msg += "\n" + "\n".join(conversion)
    msg += "\n---\n"
    msg += "\n[^(1 Schmeckle = $148 USD)](https://www.reddit.com/r/IAmA/comments/202owt/we_are_dan_harmon_and_justin_roiland_creators_of/cfzfv79)^( | price match not guaranteed |) [^(`what is my purpose`)](https://github.com/Elucidation/schmeckle_bot 'convert Schmeckles to USD')"
    return [quote, conversion, values, msg]

  return None

# Filename containing list of comment ids that have already been processed, updated at end of program
processed_filename = "comments_already_processed.txt"
def loadProcessed():
  if not os.path.isfile(processed_filename):
    print("Starting new processed file")
    return set()
  else:
    print("Loading existing processed file...")
    with open(processed_filename,'r') as f:
      return set(f.readlines())

def saveProcessed(already_processed):
  with open(processed_filename,'w') as f:
    for comment_id in already_processed:
      f.write("%s\n" % comment_id)

#########################################################
# Main Script
# Track commend ids that have already been processed successfully

# Load list of already processed comment ids
already_processed = loadProcessed()
print("Starting with already processed", already_processed)

# Will hold response data
data = []

try:
  # Read in comments from accessor and process them  
  for comment in comments:
    # Ignore self comments or comments that have been processed already
    if comment.author.name == schmeckle_bot_name or comment.id in already_processed:
      continue
    
    # If there is a schmeckle value in body
    response = getResponse(comment.body)
    if response:
      data.append([comment, response])
      # Keep track of comments replied to
      already_processed.add(comment.id)
except KeyboardInterrupt:
  print("Exiting...")
finally:
  saveProcessed(already_processed)

print(already_processed)

# TODO: do something with data, reply to comments
# TODO: handle print() unicode error at some point
# TODO: track comments that have been replied to in a deque cache to avoid repeats
# TODO: save comments replied to in txt file, load on start