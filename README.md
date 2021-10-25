
# Podcon

Conversational analysis of your favourite podcasts using AI.

## Demo

This application was built for the API:world hackathon and can be tested at [this]() site.
  
## Environment Variables

To run this project, you will need to add the following environment variables to your .env file

`API_KEY`

`API_SECRET`

Get these from your podcastindex developer console

`APP_ID`

`APP_SECRET`

Get these from your symbl.ai developer console
## Lessons Learned


I learned how to use [htmx]() with flask to create a "SPA" like application.

Some challenges I have faced is using the podcast index api returns a redirect url for the actual podcast mp3, symbl does not currently support redirect urls.
I would like to solve this by temporarily downloading the episode and sending a file to symbl rather than a url.
## Acknowledgements

 - [Symbl.ai](https://symbl.ai)
 - [API:World Hackathon](https://api-world-hackathon-2021.devpost.com)
 - [Readme](https://readme.so/editor)
## Roadmap

- Support for redirect urls

- Add a login system that allows for more than 10 episodes of a podcast to be queried
- Better fuzzy searching

  
## License

[MIT](https://choosealicense.com/licenses/mit/)

  
