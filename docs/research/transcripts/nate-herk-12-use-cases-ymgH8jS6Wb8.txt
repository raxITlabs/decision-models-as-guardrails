So Jev is literally everywhere and I
think it's going to change how AI
automations are built. So I came in here
and tested it on 12 use cases and
compared it with other AI models on
things like speed and cost. I was even
able to build this Chrome extension that
will label X tweets as breaking or, you
know, golden nuggets or AI slop in real
time for me. On the back end you can see
that it uses Jev to actually instantly
categorize all the stuff as soon as it
enters my screen. It's not doing very
well in the first hour, but I also made
this Jev trader, which is literally
every single second analyzing if
Bitcoin's going to go up or go down or
stay and then it basically places trades
in real time for me. Because this model
is so good at quick decisions. But
anyways, by the end of this video you'll
understand how Jev works and where you
should actually use it in your life. So
let's not waste any time and just get
straight into this one. All right, we're
going to start off with just like what
is Jev? I'm not going to do a super
super deep dive, just enough for you to
understand how it works and what we're
looking at in today's video. So the
interesting thing about Jev is that it's
an AI that makes decisions, but it
doesn't write anything. It doesn't
output tokens. It's not anything that
you could actually have a conversation
with. It just makes decisions. So here
was kind of the announcement tweet from
Diogo. He co-invented ChatGPT and then
he has been building in the past 2 years
this new way to train models, RLCD. And
you can see what that stands for is
reinforcement learning for calibrated
decisions. And this is on TypeSafety's
blog and by the way, if you want to
actually get in here so that you can
start playing around with Jev, then go
to TypeSafe AI and join the waitlist and
then hopefully in a few hours you're
able to sign in. But also this is
available through like Vercel's gateway
as well as OpenRouter. So if you're not
in the waitlist yet, then you can still
go out and play with Jev. But anyways,
essentially what happens is instead of a
normal chat model where you would send
in a message like this. This is some
sort of support ticket and the AI model
would read it, would reason, would think
and then output like a message or output
some sort of classification. It
basically just outputs these types of
things, which are a yes or no confidence
level, a category and sort of a score.
So for the first one, is it urgent? 99%
confidence is yes, it is urgent. Which
team? There were probably multiple
routes like technical or billing or
support, and it labeled it as technical.
And then how frustrated, it gave it a
one out of two on the frustration score
or scale. But you're fully in control.
You basically will set up Jev with,
"Hey, this is essentially how you're
supposed to make decisions, and here is
sort of like the classification
criteria." So, it's three types of
decisions, like I said. The yes or no is
called a null. The pick one is a choice,
and then we have an actual score. And
I'm going to show you guys real examples
of all of these being run on these 12
use cases, so don't worry. But I just
wanted to sort of lay the foundation
here. So, like I said, in this example,
it's yes or no, and there's a confidence
score. And the team or categorization
example, it's different categories, as
well as a confidence score, and then a
score from zero to 10 on some sort of
scale. And in here, one meant that they
were frustrated. And the reason why this
is getting so much traction is because
Diogo said that this is 20 to 200 times
faster and 40 to 400 times cheaper, with
output tokens being free. And so, if we
look at the speed here, compared to
models like Terra and Luna and Sol, this
thing is going to be a lot faster. This
was just one very quick test I ran. This
doesn't mean that Terra's always faster
than Luna, but this was just one quick
example of how significantly faster Jev
is. Once again, it doesn't have to
output all these tokens or reason. It
just, boom, makes a decision and outputs
it in like this JSON format. And same
thing from a cost perspective, if you
were running thousands and thousands of
decisions per day, this is what it could
actually end up looking like. Now,
obviously, the important thing is you're
paying a lot less, so you want to make
sure that the quality is the exact same
as what you'd be getting here or here to
justify it. If we're just looking at the
cost right now, it is significantly
cheaper, and it is proven that it's
significantly cheaper. So, what it
cannot do is write or summarize or find
themes or do deep analysis. It basically
just
outputs decisions. And one other
limitation right now is that it has a
very small input context window. It's
64,000 tokens, whereas a lot of the
models that we're used to using today,
whether that be Claude or GPT, are more
on the side of a million tokens. So, if
we look at this on a use case like a
YouTube comments, if I fed in 5,000
YouTube comments, Jev could sort them
for way cheaper and way faster than any
AI model could, and then it could
categorize them as like, "Hey, these
need a reply. These are stuck. These
people want to buy." And then what you
could do is feed it a more intelligent
AI model, an AI model that actually
responds to things and outputs things.
And you could say, "Hey, ChatGPT, could
you read just these now and then help me
like analyze themes or help me respond
to these ones or something like that."
And that way you're not using a slower
and more expensive model to actually
categorize all of those comments in the
first place. Because Jev isn't a
frontier AI model. It's not even in the
same bucket as Astra or Fable. It's a
completely different type of model. So,
when to use it? If you have thousands of
things, if you have a corpus of data, if
you need to classify things, make
decisions, or you're running some sort
of decision-based or
classification-based workflow at scale
and production. If you need like very
quick real-time decisions because it's
really, really fast. And stay with
ChatGPT if you need things like handful
of items, you need to understand why,
you need to brainstorm, you need to
chat, things like that. Anyways, let's
just get straight into some use cases
here. So, I know this might look a
little bit intimidating of a screen.
But, what I want to show you is
a little bit of a playground of how this
actually works. By the way, guys, I've
got this completely free SOP for you
about getting your first AI automation
clients. It's going to go over the exact
steps that has been proven for hundreds
of our AIS+ members to get their first
paid gigs. It goes over the one-sentence
service pitch that can get you started
today, why your first client should cost
you money, the five-minute video that
answers, "Can this person actually
deliver?" before you've actually
received any money, what to do when you
have zero case studies. There's so many
good things in here that are going to
help you out. Even if you already do
have clients, I would recommend grabbing
this because like I said, it's yours
completely free. So, if you want to grab
this, there's a link for it down in the
description. Let's get back to the
video. So, the first one we're looking
at is emails. Now, real quick, you can
see that I've got a bunch of different
categories set up or a bunch of
different questions set up. The first
one is invoice or receipt. This is a yes
or no. The second one is brand deal.
This is yes or no. Scammer fishing, yes
or no. We also have email type. We also
have urgency, and we also have sponsor
fit. So, we've got different types of
scoring and different types of
categorization. And you can see here, if
I run this real quick, if I go to redo
everything and I hit run, we're
currently using the model Jev, and this
is 1,000 emails. Like, look how quick
this is able to classify 1,000 emails.
So, it did that in about 70 seconds for
9 cents. Now, obviously, that's not like
super super fast, like lightning fast,
but this was not parallelized. If we
were to run all of those individually in
parallel, it would have been so much
faster. But, I just wanted to show the
difference here. Let's even go to
something like GPT 5.6 Luna, and we'll
run this again on everything. So, all
1,000. I mean, this feels like it took
forever. With Luna, that took 5 minutes,
and it was 62 cents, compared to 70
seconds, and I think it was 9 cents. And
also, think about it wasn't just doing
one sort of classification, it was doing
all seven of these rules. And I actually
just changed the back end to make this
actually process things more in parallel
with bigger payloads. So, I'm just going
to run this now, and we'll see how much
quicker this really is. Boom. Look how
fast that went. That took 6 seconds, and
it once again was 9 cents. So, that just
shows how you can optimize that back end
to make Jev go even faster. And yes, you
can do the same thing with Luna, but
it's just not going to be as fast as 6
seconds for 1,000 emails across seven
categories. So, I know that this
interface may be a little overwhelming.
Let's just get rid of everything here
except for invoice or receipt. So, this
is literally just us saying, "Okay, we
want to set up some sort of
classification for all of these 1,000
emails. We're going to give it a name.
We're going to ask the question, is this
email a receipt, invoice, payment
confirmation, or billing notice?" And
then we just define like what counts as
yes. So, it has a a charge, a payment, a
payout, or some sort of failed payout,
and we call it a yes when Jev is at
least 50% confident. So, that's kind of
the thing that we're running here, and I
would just go ahead and choose redo
everything. And so, when we run this,
it's basically going to look at all
1,000 of those emails and just decide,
"Is that an invoice or receipt?" It
comes back in 4 seconds for 5 cents, and
it where it landed was no on 763 of
them, but yes on 237 of them. Here is a
category example where we actually set
up the email type, whether it's
notification, newsletter, billing,
opportunity. And you can see if I edit
this, what we did is we actually had to
choose the options and define each of
them. So, this is a pretty standard AI
classification type of automation. But
then if we look at the scoring, so for
example, if we look at the sponsor fit,
if I go to what this one looks like,
this is rating it on a scale and we
basically choose from lowest to highest
what that looks like as far as not a
sponsorship inquiry at all, or if it's a
strong fit. And it will choose the
level. So, you can see here, it shows
that 942 of them were won and then it
you know, we didn't have any that were
strong fits. You can see there was
another score one that was urgency about
if there was action needed or nothing
needed at all. And this was a little bit
more even across the board. The average
was 2.8 out of five. So, anyways, email
classification is one example and
obviously when you're looking at the
actual cost and speed here, that first
example we ran, Luna was 12 times the
cost and 46 times the time and that was
also just Luna. What if we went up to
Terra and Sol? How much more expensive
that would have been and how much more
that would have cost us? So, a lot of
these use cases are kind of on the
classification side. I did the exact
same thing here with YouTube comments
where I can choose categories or yes and
no and score and I can analyze thousands
of comments at a time on things like
comment type, if they're worth a reply,
if it gives me a video idea, what the
sentiment is, what the question
difficulty is. And once again, if I run
Jev on all of a thousand of these, look
how quick that actually goes. It would
be so much longer if we used any other
sort of AI model. 5 seconds for 5 cents.
And if we actually go to my Jev console
real quick and I go ahead and refresh,
this is going to show that I've used 85
cents with Jev. But look how many
requests I've done. I've done almost
20,000 requests. Think about what 20,000
requests on a different AI model would
have cost us. And I can also do the
exact same thing with my school posts. I
can set up my custom categories or my
custom classification criteria to see
what type of questions we have, if they
need help, if we need a team answer, if
there's churn risk, member experience
level, testimonial strength. And yes,
this is kind of like a dashboard
playground view, but what if you had
this in an actual automation? Where
every single time a new post got made,
you updated the database. Every single
time a new YouTube comment came in, you
updated the database. Every time there's
a new internal CRM entry or every time
there's a new lead that submitted a form
on your website. There's so many things
you can do here and even though the
speed might not not matter a ton when it
comes to like actually having
automations in production, what does add
up really quickly is the cost. Because
once again, when you start to run
thousands and thousands of requests
through, it's going to add up big time.
So, when you talk about AI economics and
model routing, this is definitely going
to be a game changer. Now, here's
another interesting one where the speed
really did matter. I have this one
called X feed where it basically like
pulled in a bunch of posts on my feed
and it will tell me are they on topic or
you know, like what's the category? Is
it breaking news? Is there video idea
potential? So, similar classification as
we saw on these first three, but look
what else I did. If I give my X a hard
refresh real quick, you'll see that in
the bottom left I have this thing called
Jev Judged. And you can see that it
judged that one a slop and as I scroll
through, this is a Chrome extension that
I built for me where it's looking at the
X posts and really quickly reading them
and classifying them as breaking or
golden nuggets or AI slop. It's
basically going to help me keep me more
focused while I'm scrolling through X to
see, you know, like highlighting what
might be good to read and what are
things that I should probably just
ignore because of AI slop. And those are
just a Chrome extension that I built
where I has Jev on the back end powering
all of this. So, that is a pretty cool
use case and it shows how fast this
thing actually happens in production. I
mean, look how fast it's reacting to
these posts as they come onto my screen.
It's basically instant. I also thought
about what you could do with your
meetings here. You could analyze
meetings as they get transcribed in
Fireflies or Granola or whatever you use
and as soon as they come in, you can
categorize them by what type of call it
was, if you had decisions made, if you
had like action steps. I thought this
one was an interesting one because let's
say you see that in a lot of your calls
you have no next steps discussed or
defined clearly with ownership and
timelines, then you can use the data to
change how you're conducting your calls.
So, what I think is interesting is Jev
on its own doesn't analyze things for
you. But if you're strategic with the
way that you set up the questions, you
can get analysis from it. You can have
this data tell a story. You can't have
Jev look at thousands of transcripts and
say, "Hey, tell me what I need to do
better about these meetings or tell me
common themes." But what you can do is
you can give it categories and you can
give it scores and then from all of
these different types of questions that
you set up, you tell your own story with
that data. You can see that there's not
much tension in some of our calls. I
mean, this one has
Someone says they're frustrated or
overloaded, but but all of these
questions that I created for Jev here,
there's some sort of takeaway from each
of these. Are things waiting on Nate? Is
there revenue relevance? Things like
that. And I also tried this use case
with video clips where I basically had
Jev or I had, you know, Astra break up a
bunch of my YouTube videos into clips
and then I had Jev look at those clips
and tell me, you know, is this possible
to be posted on its own as a clip? A lot
of them, no. What is the hook strength
of these clips? What type of clips are
these? Do I need the screen on them? Is
there a quotable line inside of this
clip? And then I could start to have it
pull out things that might be worth
reposting somewhere else or might be
worth me thinking about the way that I
actually speak in these videos and
things like that. And so these were a
lot of ways that I would think about how
do I take a corpus of information, a ton
and ton of data that I want to have AI
analyze, but instead of paying more for
it and waiting longer, let's figure out
how we can
use the right questions to have Jev do
it for us. And then, not only can we
maybe have some sort of dashboard view,
but how do we build Jev into our actual
back-end automations where it's really
going to benefit us to having a really
cheap and fast model as we increase the
throughput. Now, I will say don't just
plug in Jev and trust what it says
automatically. What you're really going
to want to do is run evals, meaning
you're going to have a golden data set
of 100 use cases and 100 correct answers
and then you're going to run Jev through
those and you're going to run Opus
through those and you're going to run
Soul through those and you're going to
see which model gives you the best
balance of accuracy and cost. And if you
care about speed in that use case, then
also speed as well. But here's some
other things you could do. You could
have it vet contracts for you as they
come in. You could see the type of risk,
you could see the type of clause, you
could create any sort of questions that
actually matter to you when you're
vetting contracts. Same thing with jobs
and leads. You can get red flags, you
can get lead quality, you can get next
steps. You can also do something like a
brain dump router where you're
constantly just talking into your phone
or you're talking into something and
then you're feeding that into Jev and it
can tell you what type of things you're
talking about, if they're ideas or tasks
or journals. If you have things that
have deadlines, if you have things that
are high priority, what area of your
life they're in. There's so many ways to
use this because a big part of what we
do with AI, like I said, is just
figuring out what to do with all of our
data and Jev can do that really well.
And then I think one of the best
examples here is customer support. Just
routing emails around, figuring out, you
know, sentiment, urgency, what we need
to do, how we categorize these sorts of
things. I think that this is going to be
a huge game changer for customer support
because there's so many different like
decisions that have to be made and Jev
is really good and really fast and
really cheap at making decisions. So,
here's another use case that I thought
would be cool to just sort of like POC.
So, this is paper trading. This isn't
very vetted. There's a lot that's like
wrong with this, but I think that Jev
being so real-time and making decisions
so fast, it's going to be really
interesting to see how it affects things
like day trading or trading crypto in
real time. So, you can see every single
second Jev is basically predicting, is
this going to go up? Am I unclear? Is it
going to go down? You can see these
confidence scores jumping around every
single second and that's how it decides
what to do. That's how it decides down
here to place trades, to buy things or
to sell things. Now, unfortunately,
there's a lot of these fees here. So,
the fees are way more expensive than Jev
actually um making decisions for us. So,
that's one issue where it's like, okay,
well, how much would we actually have to
be able to profit to make this worth it?
But right here you can see just the cost
of running these decisions. Look how
much more this would have cost us per
day with other models. Whereas Jev would
just be costing us about two bucks a day
to run this 24/7 and Soul and Opus and
Fable would be significantly more than
Jev. Now, I've also seen people on X
doing things like having Jev play video
games and having Jev like do different
creative fun things and I think it's
really cool, like the browser use and
all that. It's cool to see what's
possible, but I think you have to think
about where's the handoff because with
browser use it was unable to like
actually type things in. It would
basically make decisions and then it
would have to route to a different model
that's better with actually controlling
the browser to do things. And that's why
I wanted to show what this looks like
for these examples because I think
building dashboards or automations where
you have Jev powering it on the back end
for things that you actually care about
in your life like these sorts of things
is where you'll start to play with Jev
and actually get some return and then
later figure out how you can expand or
extend your workflows with other models
on the back. But anyways, I hope seeing
these examples even though all of these
were very similar in the you know the
the realm of classification. I hope that
it helps you understand how you can
start to ask the right questions in here
and how you can start to work it into
things that you're doing to actually
make sense out of it. But that is going
to do it for this one. So if you guys
enjoyed and learned something new,
please give it a like it helps me out a
ton. And as always, I appreciate you
guys making it to the end of the video
and I'll see you on the next one.
Thanks everyone.
