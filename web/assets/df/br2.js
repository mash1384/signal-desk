import { mount } from './bc.js';
import { briefLayout } from './bv.js';
mount((D,dy,S) => briefLayout(D,dy,S,matchMedia('(min-width: 1040px)').matches,window.DF_G || 'heat'));
