import React, { useState } from 'react';
import {
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  List,
  ListItem,
  ListItemText,
  makeStyles,
  Grid,
  CircularProgress
} from '@material-ui/core';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import axios from 'axios';

// Leaflet ikon sorunu için geçici çözüm
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

const useStyles = makeStyles((theme) => ({
  root: {
    marginTop: theme.spacing(4),
  },
  paper: {
    padding: theme.spacing(3),
  },
  button: {
    marginTop: theme.spacing(2),
  },
  fileInput: {
    marginTop: theme.spacing(2),
    marginBottom: theme.spacing(2),
  },
  list: {
    marginTop: theme.spacing(2),
  },
  loading: {
    display: 'flex',
    justifyContent: 'center',
    marginTop: theme.spacing(2),
  },
  map: {
    height: '400px',
    width: '100%',
    marginTop: theme.spacing(2),
  },
}));

function App() {
  const classes = useStyles();
  const [adres, setAdres] = useState('');
  const [sonuclar, setSonuclar] = useState([]);
  const [yukleniyor, setYukleniyor] = useState(false);
  const [dosya, setDosya] = useState(null);
  const [mapCenter, setMapCenter] = useState([41.0082, 28.9784]); // İstanbul merkezi

  const handleAdresAra = async () => {
    if (!adres) return;
    
    setYukleniyor(true);
    try {
      const response = await axios.post('http://localhost:8000/en-yakin-subeler/', {
        adres: adres
      });
      setSonuclar(response.data);
      
      // Harita merkezini ilk şubeye göre güncelle
      if (response.data.length > 0) {
        const ilkSube = response.data[0];
        setMapCenter([ilkSube.latitude, ilkSube.longitude]);
      }
    } catch (error) {
      alert('Arama sırasında bir hata oluştu: ' + error.message);
    }
    setYukleniyor(false);
  };

  const handleDosyaYukle = async () => {
    if (!dosya) return;

    const formData = new FormData();
    formData.append('file', dosya);

    setYukleniyor(true);
    try {
      const response = await axios.post('http://localhost:8000/excel-yukle/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      alert(response.data.message);
    } catch (error) {
      alert('Dosya yükleme sırasında bir hata oluştu: ' + error.message);
    }
    setYukleniyor(false);
  };

  return (
    <Container className={classes.root}>
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Paper className={classes.paper}>
            <Typography variant="h5" gutterBottom>
              Excel Dosyası Yükle
            </Typography>
            <input
              type="file"
              accept=".xlsx,.xls"
              className={classes.fileInput}
              onChange={(e) => setDosya(e.target.files[0])}
            />
            <Button
              variant="contained"
              color="primary"
              onClick={handleDosyaYukle}
              disabled={!dosya || yukleniyor}
            >
              Dosyayı Yükle
            </Button>
          </Paper>
        </Grid>

        <Grid item xs={12}>
          <Paper className={classes.paper}>
            <Typography variant="h5" gutterBottom>
              En Yakın Şubeleri Bul
            </Typography>
            <TextField
              fullWidth
              label="Adresinizi girin"
              value={adres}
              onChange={(e) => setAdres(e.target.value)}
              variant="outlined"
            />
            <Button
              className={classes.button}
              variant="contained"
              color="primary"
              onClick={handleAdresAra}
              disabled={!adres || yukleniyor}
              fullWidth
            >
              Şubeleri Bul
            </Button>

            {yukleniyor && (
              <div className={classes.loading}>
                <CircularProgress />
              </div>
            )}

            {sonuclar.length > 0 && (
              <>
                <MapContainer
                  center={mapCenter}
                  zoom={13}
                  className={classes.map}
                >
                  <TileLayer
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                  />
                  {sonuclar.map((sube) => (
                    <Marker
                      key={sube.sube_id}
                      position={[sube.latitude, sube.longitude]}
                    >
                      <Popup>
                        <b>{sube.sube_ad}</b><br />
                        Mesafe: {sube.mesafe} km<br />
                        Tahmini Süre: {sube.tahmini_sure}
                      </Popup>
                    </Marker>
                  ))}
                </MapContainer>

                <List className={classes.list}>
                  {sonuclar.map((sube) => (
                    <ListItem key={sube.sube_id} divider>
                      <ListItemText
                        primary={sube.sube_ad}
                        secondary={`Mesafe: ${sube.mesafe} km - Tahmini Süre: ${sube.tahmini_sure}`}
                      />
                    </ListItem>
                  ))}
                </List>
              </>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
}

export default App; 